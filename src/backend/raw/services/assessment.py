"""Deterministic assessment services shared by the graph and the API."""

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from raw import config_store
from raw.domain import DIMENSIONS, plain
from raw.models import Assessment, AssessmentControl, ChangeRequest, Control, Extraction, FactorRating, PolicyChunk
from raw.rag.text import tokenize
from raw.scoring.engine import ControlInput, FactorInput, score
from raw.scoring.rules import evaluate_rules

DIM_QUERIES = {
    "PRD": "product risk features cross-border cash prepaid virtual assets anonymity",
    "CUS": "customer risk due diligence segment beneficial ownership",
    "GEO": "geographic risk jurisdictions high-risk monitored sanctions new market",
    "CHN": "delivery channel non-face-to-face onboarding agents API",
    "TRX": "transaction risk value volume instant payments monitoring",
    "TPV": "third party vendor outsourcing due diligence custody processor",
}


def latest_extraction(session: Session, cr_id: int, confirmed_only: bool = False) -> Extraction | None:
    q = select(Extraction).where(Extraction.cr_id == cr_id)
    if confirmed_only:
        q = q.where(Extraction.confirmed_at.is_not(None))
    return session.execute(q.order_by(Extraction.version.desc()).limit(1)).scalar_one_or_none()


def latest_assessment(session: Session, cr_id: int) -> Assessment | None:
    q = select(Assessment).where(Assessment.cr_id == cr_id).order_by(Assessment.version.desc()).limit(1)
    return session.execute(q).scalar_one_or_none()


def case_config(session: Session, cr: ChangeRequest) -> dict[str, Any]:
    cv = config_store.get(session, cr.config_version_id) if cr.config_version_id else config_store.active(session)
    return cv.content


def dim_name(cfg: dict[str, Any], dim: str) -> str:
    return cfg["scoring"]["dimensions"][dim]["name"]


def retrieval_query(dim: str, facts: dict[str, Any]) -> str:
    extra = {
        "PRD": [k for k in ("cross_border", "cash", "crypto", "anonymous_or_prepaid", "instant_payments") if facts.get(k)],
        "CUS": facts.get("customer_types") or [],
        "GEO": facts.get("geographies") or [],
        "CHN": facts.get("channels") or [],
        "TRX": ["instant payments"] if facts.get("instant_payments") else [],
        "TPV": facts.get("third_party_roles") or [],
    }[dim]
    words = " ".join(str(x).replace("_", " ") for x in extra)
    return f"{DIM_QUERIES[dim]} {words}".strip()


def context_pack(cr: ChangeRequest, facts: dict[str, Any], cfg: dict[str, Any], warnings: list[str]) -> str:
    """Compact case summary shared by every LLM node instead of raw documents (~150-300 tokens)."""
    cats = cfg["jurisdictions"]
    lookup = {n.lower(): c for c, names in cats.items() for n in names}
    geos = ", ".join(f"{g} ({lookup.get(g.lower(), 'unlisted')})" for g in facts.get("geographies") or []) or "not stated"
    flags = [k for k in ("cross_border", "cash", "crypto", "instant_payments", "anonymous_or_prepaid") if facts.get(k)]
    value = facts.get("monthly_value_usd")
    lines = [
        f"{cr.ref} | {cr.change_type} | {cr.business_line} | {cr.title}",
        f"customers: {', '.join(facts.get('customer_types') or []) or 'not stated'}",
        f"geographies: {geos}",
        f"channels: {', '.join(facts.get('channels') or []) or 'not stated'}",
        f"third parties: {', '.join(facts.get('third_parties') or []) or 'none'} "
        f"[{', '.join(facts.get('third_party_roles') or [])}]",
        f"flags: {', '.join(flags) or 'none'}",
        f"monthly value USD: {value:,.0f}" if isinstance(value, (int, float)) else "monthly value USD: not stated",
        f"proposed controls: {'; '.join(facts.get('proposed_controls') or []) or 'none'}",
    ]
    if warnings:
        lines.append("warnings: " + "; ".join(warnings[:5]))
    return "\n".join(lines)


def build_assessment(session: Session, cr: ChangeRequest, extraction: Extraction, retrieval: dict[str, Any]) -> Assessment:
    """Create a new assessment version with rule-based factors and mapped controls.

    Dimensions without a fired rule are returned with origin='pending' for the
    AI suggester. Human factor overrides from the previous version carry forward.
    """
    if cr.config_version_id is None:
        cr.config_version_id = config_store.active(session).id
    cfg = case_config(session, cr)
    facts = plain(extraction.data)
    prev = latest_assessment(session, cr.id)
    a = Assessment(cr_id=cr.id, version=(prev.version + 1) if prev else 1, config_version_id=cr.config_version_id,
                   extraction_id=extraction.id, retrieval=retrieval)
    session.add(a)
    session.flush()

    carried = {f.dimension: f for f in (prev.factors if prev else []) if f.origin == "human"}
    outcomes = evaluate_rules(facts, cfg)
    for dim in DIMENSIONS:
        if dim in carried:
            h = carried[dim]
            session.add(FactorRating(assessment_id=a.id, dimension=dim, likelihood=h.likelihood, impact=h.impact,
                                     origin="human", rule_ids=h.rule_ids, risk_types=h.risk_types,
                                     rationale=f"Carried forward analyst override: {h.rationale}", citations=h.citations,
                                     confirmed=True, confirmed_by=h.confirmed_by))
        elif dim in outcomes:
            o = outcomes[dim]
            session.add(FactorRating(assessment_id=a.id, dimension=dim, likelihood=o.likelihood, impact=o.impact,
                                     origin="rule", rule_ids=o.rule_ids, risk_types=o.risk_types, rationale=o.rationale,
                                     citations=o.citations, confirmed=True))
        else:
            d = cfg["scoring"]["default_rating"]
            session.add(FactorRating(assessment_id=a.id, dimension=dim, likelihood=d["likelihood"], impact=d["impact"],
                                     origin="pending", rationale="awaiting suggestion", confirmed=False))

    from raw.scoring.rules import map_controls

    library = [{"id": c.id, "keywords": c.keywords, "dims": c.dims, "design": c.design, "operating": c.operating}
               for c in session.execute(select(Control)).scalars()]
    for c, kw in map_controls(facts.get("proposed_controls") or [], library):
        session.add(AssessmentControl(assessment_id=a.id, control_id=c["id"], dims=c["dims"], design=c["design"],
                                      operating=c["operating"], origin="mapped", matched_on=kw))
    session.flush()
    session.refresh(a)
    return a


def rescore(session: Session, a: Assessment, cfg: dict[str, Any]):
    session.refresh(a)
    factors = [FactorInput(f.dimension, f.likelihood, f.impact) for f in a.factors]
    controls = [ControlInput(c.control_id, tuple(c.dims), c.design, c.operating) for c in a.controls]
    r = score(factors, controls, cfg["scoring"])
    a.inherent_overall, a.residual_overall = r.inherent_overall, r.residual_overall
    a.inherent_tier, a.residual_tier = r.inherent_tier, r.residual_tier
    a.risk_types = sorted({rt for f in a.factors for rt in (f.risk_types or [])})
    trace = r.to_trace()
    trace["config_version_id"] = a.config_version_id
    trace["factors"] = {f.dimension: {"origin": f.origin, "rule_ids": f.rule_ids, "citations": f.citations,
                                      "rationale": f.rationale, "confirmed": f.confirmed} for f in a.factors}
    a.score_trace = trace
    session.flush()
    return r


def allowed_citations(session: Session, a: Assessment) -> set[str]:
    ids = {h["id"] for hits in (a.retrieval or {}).values() for h in hits}
    for f in a.factors:
        ids.update(f.citations or [])
    ids.add("AML-POL-7.1")
    ids.add("NPA-POL-2.1")
    existing = set(session.execute(select(PolicyChunk.id).where(PolicyChunk.id.in_(ids))).scalars())
    return existing


CITE_RX = re.compile(r"\[chunk:([A-Z0-9.\-]+)\]")
RATING_RX = re.compile(r"rated likelihood (\d) and impact (\d)", re.I)


def split_claims(text: str) -> list[str]:
    parts = re.split(r"(?<=\])\s+(?=[A-Z])|(?<=[.!?])\s+(?=[A-Z])", text.strip())
    claims: list[str] = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if claims and CITE_RX.fullmatch(p.strip()):
            claims[-1] += " " + p
        else:
            claims.append(p)
    return claims


def deterministic_critique(session: Session, a: Assessment, narrative: dict[str, Any]) -> list[dict[str, Any]]:
    """Check every claim: has a citation, cites an allowed chunk, rating numbers match the factor table,
    and has lexical overlap with the cited text. Returns claim records with a status."""
    allowed = allowed_citations(session, a)
    chunk_text = {c.id: c.text for c in session.execute(select(PolicyChunk).where(PolicyChunk.id.in_(allowed))).scalars()}
    factors = {f.dimension: f for f in a.factors}
    claims = []
    idx = 0
    for section in [{"dimension": "SUMMARY", "text": narrative.get("summary", "")}, *narrative.get("sections", [])]:
        for claim in split_claims(section["text"]):
            cites = CITE_RX.findall(claim)
            status, reason, overlap = "ok", "", 0.0
            if not cites:
                status, reason = "unsupported", "no citation"
            elif any(c not in allowed for c in cites):
                status, reason = "unsupported", f"cites unknown or unretrieved chunk {[c for c in cites if c not in allowed]}"
            else:
                m = RATING_RX.search(claim)
                f = factors.get(section["dimension"])
                if m and f:
                    if (int(m.group(1)), int(m.group(2))) != (f.likelihood, f.impact):
                        status, reason = "unsupported", f"rating mismatch: table says {f.likelihood}/{f.impact}"
                    else:
                        reason = "rating matches factor table"
                elif section["dimension"] == "SUMMARY":
                    reason = "summary of deterministic scores"
                else:
                    body = set(tokenize(CITE_RX.sub("", claim)))
                    src = set(tokenize(" ".join(chunk_text.get(c, "") for c in cites)))
                    overlap = len(body & src) / max(1, len(body))
                    if overlap < 0.25:
                        status, reason = "doubtful", f"low lexical overlap {overlap:.2f}"
                    else:
                        reason = f"lexical overlap {overlap:.2f}"
            claims.append({"index": idx, "dimension": section["dimension"], "text": claim, "citations": cites,
                           "status": status, "reason": reason, "overlap": round(overlap, 2)})
            idx += 1
    return claims
