from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from raw.graph import runner
from raw.models import ChangeRequest, CommitteeVote, Control, Decision, Extraction, LLMCall, Override, User
from raw.services.assessment import latest_assessment, latest_extraction
from raw.services.gates import gate_status
from raw.workflow.machine import committee_round


def _dt(v) -> str | None:
    return v.isoformat() if v else None


def case_summary(cr: ChangeRequest, users: dict[int, User], a=None) -> dict[str, Any]:
    return {
        "id": cr.id, "ref": cr.ref, "title": cr.title, "change_type": cr.change_type, "business_line": cr.business_line,
        "status": cr.status, "pipeline_state": cr.pipeline_state, "pipeline_step": cr.pipeline_step,
        "needs_human": cr.needs_human, "warnings": cr.warnings or [],
        "created_by": users[cr.created_by].name if cr.created_by in users else None,
        "created_at": _dt(cr.created_at), "updated_at": _dt(cr.updated_at),
        "residual_tier": a.residual_tier if a else None, "residual": a.residual_overall if a else None,
    }


def extraction_dict(e: Extraction | None, users) -> dict[str, Any] | None:
    if e is None:
        return None
    return {"id": e.id, "version": e.version, "data": e.data, "flags": e.flags, "provider": e.provider,
            "prompt_version": e.prompt_version, "confirmed": e.confirmed_at is not None,
            "confirmed_by": users[e.confirmed_by].name if e.confirmed_by in users else None,
            "confirmed_at": _dt(e.confirmed_at)}


def case_detail(session: Session, cr: ChangeRequest) -> dict[str, Any]:
    users = {u.id: u for u in session.execute(select(User)).scalars()}
    a = latest_assessment(session, cr.id)
    controls = {c.id: c.name for c in session.execute(select(Control)).scalars()}
    rnd = committee_round(session, cr.id)
    votes = list(session.execute(select(CommitteeVote).where(CommitteeVote.cr_id == cr.id).order_by(CommitteeVote.id)).scalars())
    decisions = list(session.execute(select(Decision).where(Decision.cr_id == cr.id).order_by(Decision.id)).scalars())
    overrides = list(session.execute(select(Override).where(Override.cr_id == cr.id).order_by(Override.id)).scalars())
    calls = list(session.execute(select(LLMCall).where(LLMCall.cr_id == cr.id)).scalars())
    assessment = None
    if a is not None:
        dims = (a.score_trace or {}).get("dimensions", {})
        assessment = {
            "id": a.id, "version": a.version, "config_version_id": a.config_version_id,
            "inherent": a.inherent_overall, "inherent_tier": a.inherent_tier,
            "residual": a.residual_overall, "residual_tier": a.residual_tier, "risk_types": a.risk_types,
            "factors": [{
                "dimension": f.dimension, "likelihood": f.likelihood, "impact": f.impact, "origin": f.origin,
                "rule_ids": f.rule_ids, "risk_types": f.risk_types, "rationale": f.rationale, "citations": f.citations,
                "confirmed": f.confirmed, **{k: dims.get(f.dimension, {}).get(k) for k in
                                             ("inherent", "mitigation", "residual", "combined_effectiveness", "floor_applied")},
            } for f in a.factors],
            "controls": [{"control_id": c.control_id, "name": controls.get(c.control_id, c.control_id), "dims": c.dims,
                          "design": c.design, "operating": c.operating, "origin": c.origin, "matched_on": c.matched_on}
                         for c in a.controls],
            "steps": (a.score_trace or {}).get("steps", []),
            "config_hash": (a.score_trace or {}).get("config_hash"),
            "retrieval": a.retrieval, "narrative": a.narrative, "narrative_provider": a.narrative_provider,
            "narrative_stale": a.narrative_stale, "critique": a.critique,
            "narrative_signed_by": users[a.narrative_signed_by].name if a.narrative_signed_by in users else None,
            "warnings_ack_reason": a.warnings_ack_reason,
        }
    try:
        waiting = runner.waiting_at(cr)
    except Exception:
        waiting = None
    return {
        **case_summary(cr, users, a),
        "description": cr.description, "launch_date": cr.launch_date, "info_request": cr.info_request,
        "config_version_id": cr.config_version_id, "graph_run": cr.graph_run, "waiting_at": waiting,
        "submitted_at": _dt(cr.submitted_at), "decision_ready_at": _dt(cr.decision_ready_at),
        "documents": [{"id": d.id, "filename": d.filename, "size": d.size, "sha256": d.sha256, "preview": d.text[:600]}
                      for d in cr.documents],
        "extraction": extraction_dict(latest_extraction(session, cr.id), users),
        "assessment": assessment,
        "gates": gate_status(session, cr),
        "overrides": [{"id": o.id, "target_type": o.target_type, "target_key": o.target_key, "old_value": o.old_value,
                       "new_value": o.new_value, "reason": o.reason, "by": users[o.user_id].name, "by_id": o.user_id,
                       "tier_before": o.tier_before, "tier_after": o.tier_after, "requires_ack": o.requires_ack,
                       "acked_by": users[o.acked_by].name if o.acked_by in users else None,
                       "created_at": _dt(o.created_at)} for o in overrides],
        "committee_round": rnd,
        "votes": [{"round": v.round, "member": users[v.user_id].name, "member_id": v.user_id, "vote": v.vote,
                   "conflict": v.conflict, "rationale": v.rationale, "conditions": v.conditions} for v in votes],
        "decisions": [{"round": d.round, "outcome": d.outcome, "conditions": d.conditions, "summary": d.vote_summary,
                       "recorded_by": users[d.recorded_by].name, "at": _dt(d.created_at)} for d in decisions],
        "ai_usage": {
            "calls": len(calls), "input_tokens": sum(c.input_tokens for c in calls),
            "output_tokens": sum(c.output_tokens for c in calls), "cache_hits": sum(c.cache_hit for c in calls),
            "fallbacks": sum(c.status == "fallback" for c in calls),
            "by_node": {n: sum(c.input_tokens + c.output_tokens for c in calls if c.node == n) for n in {c.node for c in calls}},
        },
    }
