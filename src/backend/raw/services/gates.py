"""Human gate status (docs/governance/review-gates.md)."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from raw.models import ChangeRequest, Decision, Override
from raw.services.assessment import latest_assessment, latest_extraction


def gate_status(session: Session, cr: ChangeRequest) -> dict[str, Any]:
    ext = latest_extraction(session, cr.id)
    a = latest_assessment(session, cr.id)
    g: dict[str, Any] = {}
    g["G0"] = {"passed": bool(ext and ext.confirmed_at), "label": "Product owner confirmed intake",
               "blocking": [] if ext and ext.confirmed_at else ["intake extraction not confirmed"]}
    pending = [f.dimension for f in (a.factors if a else []) if f.origin in {"ai", "offline", "pending"} and not f.confirmed]
    g["G1"] = {"passed": bool(a) and not pending, "label": "Analyst confirmed AI-suggested factors",
               "blocking": [f"AI-suggested factor {d} not confirmed" for d in pending] or ([] if a else ["no assessment"])}
    unacked = list(session.execute(select(Override).where(
        Override.cr_id == cr.id, Override.requires_ack.is_(True), Override.acked_by.is_(None))).scalars())
    g["G1b"] = {"passed": not unacked, "label": "Second analyst acknowledged tier-changing overrides",
                "blocking": [f"override #{o.id} ({o.target_key}: {o.tier_before} -> {o.tier_after}) needs a second analyst"
                             for o in unacked]}
    narrative_ok = bool(a and a.narrative and a.narrative_signed_by and not a.narrative_stale)
    blocking = []
    if not a or not a.narrative:
        blocking.append("no narrative drafted")
    elif a.narrative_stale:
        blocking.append("narrative is stale after an override: redraft or edit, then sign")
    elif not a.narrative_signed_by:
        blocking.append("narrative not signed off")
    g["G2"] = {"passed": narrative_ok, "label": "Analyst signed the narrative", "blocking": blocking}
    decided = session.execute(select(Decision).where(Decision.cr_id == cr.id)).first() is not None
    g["G3"] = {"passed": decided, "label": "Committee decision at quorum", "blocking": [] if decided else ["awaiting committee"]}
    return g


def committee_blockers(session: Session, cr: ChangeRequest) -> list[str]:
    g = gate_status(session, cr)
    return [b for k in ("G0", "G1", "G1b", "G2") for b in g[k]["blocking"]]
