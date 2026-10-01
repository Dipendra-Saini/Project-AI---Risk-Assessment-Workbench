"""Examiner pack: everything needed to explain a decision months later (FR-21)."""

import html
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from raw.audit import chain
from raw.models import (
    Assessment,
    AuditEvent,
    ChangeRequest,
    CommitteeVote,
    ConfigVersion,
    Decision,
    Extraction,
    LLMCall,
    Override,
    PolicyChunk,
    User,
)


def build_pack(session: Session, cr: ChangeRequest, actor: str) -> dict[str, Any]:
    users = {u.id: u.username for u in session.execute(select(User)).scalars()}
    assessments = list(session.execute(select(Assessment).where(Assessment.cr_id == cr.id).order_by(Assessment.version)).scalars())
    cited = {c for a in assessments for f in a.factors for c in (f.citations or [])}
    for a in assessments:
        for claim in (a.critique or {}).get("claims", []):
            cited.update(claim.get("citations", []))
    chunks = {c.id: {"title": c.section_title, "doc": c.doc_title, "text": c.text, "source_url": c.source_url}
              for c in session.execute(select(PolicyChunk).where(PolicyChunk.id.in_(cited))).scalars()}
    config_ids = {a.config_version_id for a in assessments}
    configs = {cv.version: {"hash": cv.content_hash, "note": cv.note, "content": cv.content}
               for cv in session.execute(select(ConfigVersion).where(ConfigVersion.id.in_(config_ids))).scalars()}
    events = list(session.execute(select(AuditEvent).where(AuditEvent.entity_type == "change_request",
                                                           AuditEvent.entity_id == str(cr.id)).order_by(AuditEvent.seq)).scalars())
    calls = list(session.execute(select(LLMCall).where(LLMCall.cr_id == cr.id)).scalars())
    pack = {
        "generated_at": datetime.now(UTC).isoformat(),
        "generated_by": actor,
        "case": {"ref": cr.ref, "title": cr.title, "description": cr.description, "change_type": cr.change_type,
                 "business_line": cr.business_line, "status": cr.status, "raised_by": users.get(cr.created_by),
                 "submitted_at": str(cr.submitted_at), "decision_ready_at": str(cr.decision_ready_at),
                 "warnings": cr.warnings},
        "documents": [{"filename": d.filename, "sha256": d.sha256, "size": d.size} for d in cr.documents],
        "extractions": [{"version": e.version, "provider": e.provider, "prompt": e.prompt_version, "flags": e.flags,
                         "confirmed_by": users.get(e.confirmed_by), "confirmed_at": str(e.confirmed_at), "data": e.data}
                        for e in session.execute(select(Extraction).where(Extraction.cr_id == cr.id)
                                                 .order_by(Extraction.version)).scalars()],
        "assessments": [{
            "version": a.version, "config_version_id": a.config_version_id,
            "inherent": a.inherent_overall, "inherent_tier": a.inherent_tier,
            "residual": a.residual_overall, "residual_tier": a.residual_tier, "risk_types": a.risk_types,
            "factors": [{"dimension": f.dimension, "likelihood": f.likelihood, "impact": f.impact, "origin": f.origin,
                         "rule_ids": f.rule_ids, "rationale": f.rationale, "citations": f.citations,
                         "confirmed_by": users.get(f.confirmed_by)} for f in a.factors],
            "controls": [{"control_id": c.control_id, "design": c.design, "operating": c.operating, "origin": c.origin}
                         for c in a.controls],
            "score_trace": a.score_trace, "narrative": a.narrative, "narrative_provider": a.narrative_provider,
            "critique": a.critique, "narrative_signed_by": users.get(a.narrative_signed_by),
            "warnings_ack_reason": a.warnings_ack_reason,
        } for a in assessments],
        "overrides": [{"id": o.id, "type": o.target_type, "key": o.target_key, "old": o.old_value, "new": o.new_value,
                       "reason": o.reason, "by": users.get(o.user_id), "tier_before": o.tier_before,
                       "tier_after": o.tier_after, "acknowledged_by": users.get(o.acked_by), "at": str(o.created_at)}
                      for o in session.execute(select(Override).where(Override.cr_id == cr.id)).scalars()],
        "votes": [{"round": v.round, "member": users.get(v.user_id), "vote": v.vote, "conflict": v.conflict,
                   "rationale": v.rationale, "conditions": v.conditions}
                  for v in session.execute(select(CommitteeVote).where(CommitteeVote.cr_id == cr.id)).scalars()],
        "decisions": [{"round": d.round, "outcome": d.outcome, "conditions": d.conditions, "summary": d.vote_summary,
                       "recorded_by": users.get(d.recorded_by), "at": str(d.created_at)}
                      for d in session.execute(select(Decision).where(Decision.cr_id == cr.id)).scalars()],
        "cited_policy": chunks,
        "scoring_configs": configs,
        "ai_usage": {"calls": len(calls), "input_tokens": sum(c.input_tokens for c in calls),
                     "output_tokens": sum(c.output_tokens for c in calls),
                     "providers": sorted({f"{c.provider}:{c.model}" for c in calls}),
                     "prompts": sorted({f"{c.prompt_id}@{c.prompt_version}" for c in calls})},
        "audit_events": [{"seq": e.seq, "ts": e.ts, "actor": e.actor, "action": e.action, "payload": e.payload,
                          "hash": e.hash, "prev_hash": e.prev_hash} for e in events],
        "chain_verification": chain.verify(session),
    }
    chain.record(session, actor, "examiner_pack.exported", "change_request", cr.id,
                 {"events": len(events), "chain_valid": pack["chain_verification"]["valid"]})
    return pack


def to_html(pack: dict[str, Any]) -> str:
    e = html.escape
    c = pack["case"]
    latest = pack["assessments"][-1] if pack["assessments"] else None
    rows = ""
    if latest:
        dims = latest["score_trace"].get("dimensions", {})
        for f in latest["factors"]:
            d = dims.get(f["dimension"], {})
            rows += (f"<tr><td>{e(f['dimension'])}</td><td>{f['likelihood']}</td><td>{f['impact']}</td>"
                     f"<td>{d.get('inherent', '')}</td><td>{d.get('mitigation', '')}</td><td>{d.get('residual', '')}</td>"
                     f"<td>{e(f['origin'])} {e(', '.join(f['rule_ids'] or []))}</td><td>{e(', '.join(f['citations'] or []))}</td></tr>")
    overrides = "".join(f"<li>#{o['id']} {e(o['type'])} {e(o['key'])} by {e(str(o['by']))}: {e(o['reason'])} "
                        f"({e(str(o['tier_before']))} &rarr; {e(str(o['tier_after']))})</li>" for o in pack["overrides"])
    votes = "".join(f"<li>{e(str(v['member']))}: {e(str(v['vote']))}{' (conflict declared)' if v['conflict'] else ''} - "
                    f"{e(v['rationale'])}</li>" for v in pack["votes"])
    decision = pack["decisions"][-1] if pack["decisions"] else None
    decision_text = (f"{e(decision['outcome'])} - conditions: {e('; '.join(decision['conditions']) or 'none')}"
                     if decision else "No decision yet")
    events = "".join(f"<tr><td>{x['seq']}</td><td>{e(x['ts'][:19])}</td><td>{e(x['actor'])}</td><td>{e(x['action'])}</td>"
                     f"<td><code>{x['hash'][:12]}</code></td></tr>" for x in pack["audit_events"])
    narrative = ""
    if latest and latest["narrative"]:
        narrative = f"<p>{e(latest['narrative'].get('summary', ''))}</p>" + "".join(
            f"<h4>{e(s['dimension'])}</h4><p>{e(s['text'])}</p>" for s in latest["narrative"].get("sections", []))
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Examiner pack {e(c['ref'])}</title>
<style>body{{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;color:#111}}table{{border-collapse:collapse;width:100%}}
td,th{{border:1px solid #ccc;padding:4px 6px;font-size:13px;text-align:left}}h1{{margin-bottom:0}}.muted{{color:#555}}</style></head><body>
<h1>Examiner pack - {e(c['ref'])}</h1><p class="muted">{e(c['title'])} | {e(c['change_type'])} | {e(c['business_line'])}
| status {e(c['status'])} | generated {e(pack['generated_at'][:19])} by {e(pack['generated_by'])}</p>
<p><b>Audit chain:</b> {'VALID' if pack['chain_verification']['valid'] else 'BROKEN'}
({pack['chain_verification']['events']} events, head {e(pack['chain_verification'].get('head_hash', '')[:16])})</p>
<h2>Decision</h2><p>{decision_text}</p>
<h2>Risk scores (assessment v{latest['version'] if latest else '-'}, config v{latest['config_version_id'] if latest else '-'})</h2>
<p>Inherent {latest['inherent'] if latest else ''} ({latest['inherent_tier'] if latest else ''}) &rarr;
Residual {latest['residual'] if latest else ''} ({latest['residual_tier'] if latest else ''})</p>
<table><tr><th>Dim</th><th>L</th><th>I</th><th>Inherent</th><th>Mitigation</th><th>Residual</th><th>Origin</th><th>Citations</th></tr>{rows}</table>
<h2>Narrative</h2>{narrative}<h2>Overrides</h2><ul>{overrides or '<li>none</li>'}</ul>
<h2>Committee votes</h2><ul>{votes or '<li>none</li>'}</ul>
<h2>AI usage</h2><pre>{e(json.dumps(pack['ai_usage'], indent=1))}</pre>
<h2>Audit trail</h2><table><tr><th>Seq</th><th>Time</th><th>Actor</th><th>Action</th><th>Hash</th></tr>{events}</table>
</body></html>"""
