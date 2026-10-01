"""Assessment graph nodes. Each node has one job, opens its own DB session,
is traced, timed and failure-isolated (a failing node never blocks the case)."""

import functools
import logging
import time
from dataclasses import asdict
from typing import Any

from langgraph.errors import GraphInterrupt
from langgraph.types import interrupt
from sqlalchemy import select

from raw.audit import chain
from raw.db import session_scope
from raw.domain import (
    CHANNELS,
    CUSTOMER_TYPES,
    DIMENSIONS,
    THIRD_PARTY_ROLES,
    ClassifyResult,
    CritiqueResult,
    FactorSuggestion,
    IntakeExtraction,
    Narrative,
    Status,
    plain,
)
from raw.graph.state import CaseState
from raw.llm import offline
from raw.llm.guard import screen_injection, span_in_source
from raw.llm.prompts import load_prompt
from raw.llm.router import LLMRouter
from raw.models import Assessment, ChangeRequest, Extraction, PolicyChunk
from raw.observability import metrics
from raw.observability.tracing import span
from raw.rag.retriever import HybridRetriever
from raw.services.assessment import (
    build_assessment,
    case_config,
    context_pack,
    deterministic_critique,
    dim_name,
    latest_extraction,
    rescore,
    retrieval_query,
)
from raw.workflow.machine import transition

log = logging.getLogger(__name__)
MAX_DOC_CHARS = 6000  # per document; keeps extraction prompts inside the free-tier budget
ENUMS = {"customer_types": CUSTOMER_TYPES, "channels": CHANNELS, "third_party_roles": THIRD_PARTY_ROLES}


def _add_warnings(cr: ChangeRequest, new: list[str]) -> None:
    if new:
        cr.warnings = list(dict.fromkeys([*(cr.warnings or []), *new]))


def node(name: str):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(state: CaseState) -> dict[str, Any]:
            t0 = time.monotonic()
            with span(f"node.{name}", **{"raw.cr_id": state["cr_id"]}):
                with session_scope() as s:
                    s.get(ChangeRequest, state["cr_id"]).pipeline_step = name
                try:
                    return fn(state) or {}
                except GraphInterrupt:
                    raise
                except Exception as e:
                    log.exception("node %s failed", name)
                    metrics.NODE_ERRORS.labels(name).inc()
                    msg = f"{name} failed: {type(e).__name__}: {str(e)[:160]}"
                    with session_scope() as s:
                        cr = s.get(ChangeRequest, state["cr_id"])
                        cr.needs_human = True
                        _add_warnings(cr, [msg])
                        chain.record(s, "pipeline", "pipeline.node_failed", "change_request", cr.id, {"node": name, "error": msg})
                    return {"warnings": [*state.get("warnings", []), msg]}
                finally:
                    metrics.NODE_SECONDS.labels(name).observe(time.monotonic() - t0)

        return wrapper

    return deco


@node("classify_change")
def classify_change(state: CaseState):
    with session_scope() as s:
        cr = s.get(ChangeRequest, state["cr_id"])
        if cr.change_type != "other":
            return {}  # the form field is authoritative; no tokens spent
        text = f"{cr.title}. {cr.description}"
        res = LLMRouter(s).complete_json("classify_change", {"text": text}, ClassifyResult,
                                         lambda: offline.classify(text), node="classify_change", cr_id=cr.id)
        cr.change_type = res.data.change_type.value
        chain.record(s, "pipeline", "ai.classified", "change_request", cr.id,
                     {"change_type": cr.change_type, "provider": res.provider, "confidence": res.data.confidence})
    return {}


def _normalise(data: dict[str, Any], source: str, degraded: bool) -> tuple[dict[str, Any], list[str]]:
    flags = []
    for field, allowed in ENUMS.items():
        vals = [str(v).strip().lower().replace(" ", "_").replace("-", "_") for v in data[field]["value"] or []]
        data[field]["value"] = [v for v in dict.fromkeys(vals) if v in allowed]
    data["geographies"]["value"] = list(dict.fromkeys(g.strip() for g in data["geographies"]["value"] if g and g.strip()))
    for field, item in data.items():
        item["origin"] = "offline" if degraded else "ai"
        v = item["value"]
        non_default = bool(v) if not isinstance(v, (int, float)) or isinstance(v, bool) else v is not None
        if not degraded and non_default and not span_in_source(item.get("source_span", ""), source):
            item["confidence"] = min(item.get("confidence", 0.5), 0.3)
            flags.append(f"{field}: evidence span not found in the documents; please verify")
    return data, flags


@node("extract_documents")
def extract_documents(state: CaseState):
    with session_scope() as s:
        cr = s.get(ChangeRequest, state["cr_id"])
        cfg = case_config(s, cr)
        docs = "\n".join(f"[{d.filename}]\n{d.text[:MAX_DOC_CHARS]}" for d in cr.documents)
        source = f"{cr.title}. {cr.description}\n{docs}"
        injection = screen_injection(source)
        res = LLMRouter(s).complete_json(
            "extract_intake",
            {"customer_types": ", ".join(CUSTOMER_TYPES), "channels": ", ".join(CHANNELS),
             "third_party_roles": ", ".join(THIRD_PARTY_ROLES), "change_type": cr.change_type,
             "title": cr.title, "document": source},
            IntakeExtraction,
            lambda: offline.extract(source, cfg["jurisdictions"]),
            node="extract_documents",
            cr_id=cr.id,
        )
        data, flags = _normalise(res.data.model_dump(), source, res.degraded)
        if injection:
            flags.insert(0, f"possible prompt injection in submitted text: {injection[:3]} (ignored as data)")
        if res.degraded:
            flags.append(f"extraction used the deterministic fallback ({res.fallback_reason.split(':')[0]})")
        prev = latest_extraction(s, cr.id)
        e = Extraction(cr_id=cr.id, version=(prev.version + 1) if prev else 1, data=data, flags=flags,
                       provider=f"{res.provider}:{res.model}",
                       prompt_version=f"extract_intake@{load_prompt('extract_intake').version}")
        s.add(e)
        s.flush()
        _add_warnings(cr, [f for f in flags if "injection" in f])
        chain.record(s, "pipeline", "ai.extraction", "change_request", cr.id,
                     {"extraction_version": e.version, "provider": e.provider, "prompt": e.prompt_version, "flags": flags})
        return {"extraction_id": e.id, "warnings": [*state.get("warnings", []), *flags]}


def po_gate(state: CaseState):
    """G0: the product owner confirms (or corrects) the extraction."""
    decision = interrupt({"gate": "G0", "cr_id": state["cr_id"], "extraction_id": state.get("extraction_id")})
    return {"action": decision.get("action", "confirm")}


@node("retrieve_policy")
def retrieve_policy(state: CaseState):
    with session_scope() as s:
        cr = s.get(ChangeRequest, state["cr_id"])
        ext = latest_extraction(s, cr.id, confirmed_only=True)
        if ext is None:
            raise RuntimeError("no confirmed extraction")
        facts = plain(ext.data)
        r = HybridRetriever(s)
        retrieval = {}
        for dim in DIMENSIONS:
            hits = r.search(retrieval_query(dim, facts), dims=[dim], k=3)
            retrieval[dim] = [{"id": h.chunk_id, **{k: v for k, v in asdict(h).items() if k != "chunk_id"}} for h in hits]
        pack = context_pack(cr, facts, case_config(s, cr), cr.warnings or [])
        chain.record(s, "pipeline", "rag.retrieved", "change_request", cr.id,
                     {d: [h["id"] for h in hits] for d, hits in retrieval.items()})
        return {"retrieval": retrieval, "context_pack": pack, "extraction_id": ext.id}


def _passages(s, ids: list[str], limit: int = 350) -> str:
    rows = {c.id: c for c in s.execute(select(PolicyChunk).where(PolicyChunk.id.in_(ids))).scalars()}
    return "\n".join(f"[{i}] {rows[i].section_title}: {rows[i].text[:limit]}" for i in ids if i in rows)


@node("assess_factors")
def assess_factors(state: CaseState):
    with session_scope() as s:
        cr = s.get(ChangeRequest, state["cr_id"])
        cfg = case_config(s, cr)
        ext = s.get(Extraction, state["extraction_id"])
        a = build_assessment(s, cr, ext, state.get("retrieval", {}))
        facts_text = state.get("context_pack", "")
        router = LLMRouter(s)
        for f in a.factors:
            if f.origin != "pending":
                continue
            ids = [h["id"] for h in state.get("retrieval", {}).get(f.dimension, [])]
            res = router.complete_json(
                "suggest_factor",
                {"dimension": f.dimension, "dimension_name": dim_name(cfg, f.dimension), "facts": facts_text,
                 "passages": _passages(s, ids)},
                FactorSuggestion,
                lambda ids=ids, dim=f.dimension: offline.suggest_factor(dim, cfg["scoring"]["default_rating"], ids),
                node="assess_factors",
                cr_id=cr.id,
            )
            cites = [c for c in res.data.citations if c in ids]
            f.likelihood, f.impact = res.data.likelihood, res.data.impact
            f.rationale, f.citations = res.data.rationale, cites or ids[:1]
            f.origin = "offline" if res.degraded else "ai"
            f.confirmed = False
            chain.record(s, "pipeline", "ai.factor_suggested", "change_request", cr.id,
                         {"dimension": f.dimension, "likelihood": f.likelihood, "impact": f.impact,
                          "provider": res.provider, "dropped_citations": sorted(set(res.data.citations) - set(cites))})
        s.flush()
        return {"assessment_id": a.id, "redraft_count": 0, "critic_feedback": "none"}


@node("score")
def score_node(state: CaseState):
    if not state.get("assessment_id"):
        return {}
    with session_scope() as s:
        a = s.get(Assessment, state["assessment_id"])
        cr = s.get(ChangeRequest, a.cr_id)
        r = rescore(s, a, case_config(s, cr))
        chain.record(s, "pipeline", "score.computed", "change_request", cr.id,
                     {"assessment_version": a.version, "inherent": r.inherent_overall, "residual": r.residual_overall,
                      "inherent_tier": r.inherent_tier, "residual_tier": r.residual_tier,
                      "config_version_id": a.config_version_id, "config_hash": r.config_hash})
    return {}


def _dim_rows(a: Assessment, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    dims = a.score_trace.get("dimensions", {})
    rows = []
    for f in a.factors:
        d = dims.get(f.dimension, {})
        rows.append({"dimension": f.dimension, "name": dim_name(cfg, f.dimension), "likelihood": f.likelihood,
                     "impact": f.impact, "rationale": f.rationale or "", "citations": f.citations or [],
                     "inherent": d.get("inherent", f.likelihood * f.impact), "residual": d.get("residual", 0),
                     "controls": [c["control_id"] for c in d.get("controls", [])], "origin": f.origin})
    return rows


@node("draft_assessment")
def draft_assessment(state: CaseState):
    if not state.get("assessment_id"):
        return {}
    with session_scope() as s:
        a = s.get(Assessment, state["assessment_id"])
        cr = s.get(ChangeRequest, a.cr_id)
        cfg = case_config(s, cr)
        rows = _dim_rows(a, cfg)
        ids: list[str] = []
        for r in rows:
            ids += r["citations"] + [h["id"] for h in (a.retrieval or {}).get(r["dimension"], [])[:2]]
        ids = list(dict.fromkeys([*ids, "AML-POL-7.1", "NPA-POL-2.1"]))[:14]
        chunks = {c.id: {"text": c.text} for c in s.execute(select(PolicyChunk).where(PolicyChunk.id.in_(ids))).scalars()}
        overall = {"inherent": a.inherent_overall, "residual": a.residual_overall, "inherent_tier": a.inherent_tier,
                   "residual_tier": a.residual_tier, "config_version": a.config_version_id}
        scores = "\n".join(
            f"{r['dimension']} {r['name']}: likelihood {r['likelihood']} impact {r['impact']} inherent {r['inherent']:g} "
            f"residual {r['residual']:g} origin {r['origin']} controls {','.join(r['controls']) or 'none'}" for r in rows
        ) + f"\nOVERALL inherent {a.inherent_overall:g} ({a.inherent_tier}) residual {a.residual_overall:g} ({a.residual_tier})"
        facts = plain(s.get(Extraction, a.extraction_id).data) if a.extraction_id else {}
        res = LLMRouter(s).complete_json(
            "draft_assessment",
            {"context_pack": state.get("context_pack", ""), "scores": scores, "passages": _passages(s, ids),
             "feedback": state.get("critic_feedback") or "none"},
            Narrative,
            lambda: offline.draft(rows, chunks, overall, facts),
            node="draft_assessment",
            cr_id=cr.id,
        )
        narrative = res.data.model_dump()
        narrative["sections"] = [x for x in narrative["sections"] if x["dimension"] in DIMENSIONS]
        missing = [r for r in rows if r["dimension"] not in {x["dimension"] for x in narrative["sections"]}]
        if missing:
            narrative["sections"] += offline.draft(missing, chunks, overall, facts)["sections"]
        a.narrative = narrative
        a.narrative_provider = res.provider
        a.narrative_stale = False
        a.narrative_signed_by = None
        a.narrative_signed_at = None
        chain.record(s, "pipeline", "ai.narrative_drafted", "change_request", cr.id,
                     {"assessment_version": a.version, "provider": f"{res.provider}:{res.model}",
                      "degraded": res.fallback_reason, "redraft": state.get("redraft_count", 0)})
    return {}


@node("critique")
def critique(state: CaseState):
    if not state.get("assessment_id"):
        return {"loop": False}
    with session_scope() as s:
        a = s.get(Assessment, state["assessment_id"])
        claims = deterministic_critique(s, a, a.narrative or {})
        doubtful = [c for c in claims if c["status"] == "doubtful"]
        checked_by = "deterministic"
        if doubtful:
            texts = {c.id: c.text for c in s.execute(select(PolicyChunk)).scalars()}
            prompt_claims = "\n".join(
                f"{c['index']}. CLAIM: {c['text']}\n   PASSAGE: " + " ".join(texts.get(i, "")[:300] for i in c["citations"])
                for c in doubtful
            )
            res = LLMRouter(s).complete_json("critique_claims", {"claims": prompt_claims}, CritiqueResult,
                                             lambda: offline.critique(doubtful), node="critique", cr_id=a.cr_id)
            checked_by = f"deterministic+{res.provider}"
            verdicts = {v.index: v for v in res.data.verdicts}
            for c in doubtful:
                v = verdicts.get(c["index"])
                if v is None:
                    continue
                c["status"] = "ok" if v.supported else "unsupported"
                c["reason"] = f"{c['reason']}; critic: {v.reason}"
        unsupported = [c for c in claims if c["status"] != "ok"]
        a.critique = {"claims": claims, "unsupported": len(unsupported), "checked_by": checked_by}
        metrics.CRITIC_UNSUPPORTED.inc(len(unsupported))
        chain.record(s, "pipeline", "ai.critique", "change_request", a.cr_id,
                     {"claims": len(claims), "unsupported": len(unsupported), "checked_by": checked_by})
        count = state.get("redraft_count", 0)
        loop = bool(unsupported) and count < 1 and a.narrative_provider != "offline"
        feedback = "; ".join(f"claim '{c['text'][:80]}': {c['reason']}" for c in unsupported) or "none"
        return {"unsupported": len(unsupported), "critic_feedback": feedback, "redraft_count": count + (1 if loop else 0),
                "loop": loop}


@node("handoff_to_analyst")
def handoff_to_analyst(state: CaseState):
    with session_scope() as s:
        cr = s.get(ChangeRequest, state["cr_id"])
        if cr.status == Status.IN_ASSESSMENT.value:
            transition(s, cr, Status.ANALYST_REVIEW, "pipeline", warnings=cr.warnings or [])
    return {}


def analyst_gate(state: CaseState):
    """G1/G2: the analyst reviews; the graph waits for an explicit human action."""
    decision = interrupt({"gate": "G1/G2", "cr_id": state["cr_id"], "assessment_id": state.get("assessment_id")})
    return {"action": decision.get("action", "complete"), "redraft_count": 0}
