"""Deterministic workflow state machine.

Invariant (AGENTS.md #2): only `record_decision` can enter a terminal status,
and only with a committee quorum. `transition` refuses terminal targets.
"""

from collections import Counter
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from raw.audit import chain
from raw.domain import TERMINAL_STATUSES, VOTE_TO_STATUS, Role, Status, Vote
from raw.models import ChangeRequest, CommitteeVote, Decision, User
from raw.observability import metrics

ALLOWED: dict[Status, set[Status]] = {
    Status.DRAFT: {Status.SUBMITTED},
    Status.SUBMITTED: {Status.IN_ASSESSMENT},
    Status.IN_ASSESSMENT: {Status.ANALYST_REVIEW},
    Status.ANALYST_REVIEW: {Status.IN_ASSESSMENT, Status.INFO_REQUESTED, Status.COMMITTEE_REVIEW},
    Status.INFO_REQUESTED: {Status.SUBMITTED},
    Status.COMMITTEE_REVIEW: {Status.ANALYST_REVIEW},
    Status.DEFERRED: {Status.ANALYST_REVIEW},
    Status.APPROVED: set(),
    Status.APPROVED_WITH_CONDITIONS: set(),
    Status.REJECTED: set(),
}


class TransitionError(Exception):
    pass


def _apply(session: Session, cr: ChangeRequest, to: Status, actor: str, payload: dict[str, Any]) -> None:
    frm = cr.status
    cr.status = to.value
    now = datetime.now(UTC)
    if to == Status.SUBMITTED and cr.submitted_at is None:
        cr.submitted_at = now
    if to == Status.COMMITTEE_REVIEW and cr.decision_ready_at is None:
        cr.decision_ready_at = now
        if cr.submitted_at is not None:
            sub = cr.submitted_at if cr.submitted_at.tzinfo else cr.submitted_at.replace(tzinfo=UTC)
            metrics.DECISION_READY_SECONDS.observe((now - sub).total_seconds())
    metrics.TRANSITIONS.labels(frm, to.value).inc()
    chain.record(session, actor, "case.transition", "change_request", cr.id, {"from": frm, "to": to.value, **payload})


def transition(session: Session, cr: ChangeRequest, to: Status, actor: str, **payload: Any) -> None:
    if to in TERMINAL_STATUSES:
        raise TransitionError("terminal statuses can only be set by a committee decision")
    current = Status(cr.status)
    if to not in ALLOWED[current]:
        raise TransitionError(f"cannot move from {current} to {to}")
    _apply(session, cr, to, actor, payload)


def committee_round(session: Session, cr_id: int) -> int:
    n = session.execute(select(func.count(Decision.id)).where(Decision.cr_id == cr_id)).scalar() or 0
    return n + 1


def tally(votes: list[CommitteeVote], tie_outcome: str) -> tuple[Status, dict[str, int]]:
    counts = Counter(v.vote for v in votes if not v.conflict and v.vote)
    if not counts:
        return Status(tie_outcome), {}
    ranked = counts.most_common()
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return Status(tie_outcome), dict(counts)
    return VOTE_TO_STATUS[Vote(ranked[0][0])], dict(counts)


def record_decision(session: Session, cr: ChangeRequest, user: User, workflow_cfg: dict[str, Any]) -> Decision:
    """The single path to a terminal status. Requires a human committee quorum."""
    if user.role != Role.COMMITTEE:
        raise TransitionError("only committee members can record a decision")
    if Status(cr.status) != Status.COMMITTEE_REVIEW:
        raise TransitionError("case is not in committee review")
    rnd = committee_round(session, cr.id)
    votes = list(session.execute(
        select(CommitteeVote).where(CommitteeVote.cr_id == cr.id, CommitteeVote.round == rnd)
    ).scalars())
    eligible = [v for v in votes if not v.conflict and v.vote]
    quorum = workflow_cfg["quorum"]
    if len(eligible) < quorum:
        raise TransitionError(f"quorum not met: {len(eligible)} of {quorum} eligible votes")
    outcome, counts = tally(eligible, workflow_cfg["tie_outcome"])
    conditions: list[str] = []
    for v in eligible:
        for c in v.conditions or []:
            if c not in conditions:
                conditions.append(c)
    if outcome == Status.APPROVED_WITH_CONDITIONS and not conditions:
        raise TransitionError("approval with conditions requires at least one condition")
    decision = Decision(
        cr_id=cr.id,
        round=rnd,
        outcome=outcome.value,
        conditions=conditions if outcome == Status.APPROVED_WITH_CONDITIONS else [],
        vote_summary={"counts": counts, "eligible": len(eligible), "conflicted": len(votes) - len(eligible), "quorum": quorum},
        recorded_by=user.id,
    )
    session.add(decision)
    session.flush()
    _apply(session, cr, outcome, user.username, {"decision_id": decision.id, "counts": counts})
    chain.record(session, user.username, "committee.decision", "change_request", cr.id,
                 {"outcome": outcome.value, "conditions": decision.conditions, "summary": decision.vote_summary})
    return decision
