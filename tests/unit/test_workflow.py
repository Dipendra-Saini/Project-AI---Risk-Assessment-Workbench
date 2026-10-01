import re
from pathlib import Path

import pytest

from raw.domain import TERMINAL_STATUSES, Status
from raw.models import ChangeRequest, CommitteeVote, User
from raw.workflow.machine import TransitionError, record_decision, transition

WF = {"quorum": 3, "tie_outcome": "DEFERRED"}


def _users(session):
    users = [User(username=f"c{i}", name=f"C{i}", role="committee", password_hash="x") for i in range(4)]
    po = User(username="po", name="PO", role="product_owner", password_hash="x")
    session.add_all([*users, po])
    session.flush()
    return users, po


def _case(session, po, status=Status.COMMITTEE_REVIEW):
    cr = ChangeRequest(ref="CR-T", title="t", description="d", change_type="new_product",
                       business_line="Payments", status=status.value, created_by=po.id)
    session.add(cr)
    session.flush()
    return cr


def _vote(session, cr, user, vote, conflict=False, conditions=None):
    session.add(CommitteeVote(cr_id=cr.id, user_id=user.id, round=1, vote=vote, rationale="because",
                              conflict=conflict, conditions=conditions or []))
    session.flush()


@pytest.mark.parametrize("target", sorted(TERMINAL_STATUSES))
def test_no_auto_decision_via_transition(session, target):
    _, po = _users(session)
    cr = _case(session, po)
    with pytest.raises(TransitionError):
        transition(session, cr, target, "system")


def test_no_auto_decision_static_guard():
    """No module other than the state machine may assign a terminal status."""
    root = Path(__file__).resolve().parents[2] / "src" / "backend" / "raw"
    pattern = re.compile(r"Status\.(APPROVED|APPROVED_WITH_CONDITIONS|REJECTED|DEFERRED)\b")
    offenders = []
    for py in root.rglob("*.py"):
        if py.name in {"machine.py", "domain.py"}:
            continue
        if pattern.search(py.read_text()):
            offenders.append(str(py.relative_to(root)))
    assert offenders == []


def test_illegal_transition_rejected(session):
    _, po = _users(session)
    cr = _case(session, po, Status.DRAFT)
    with pytest.raises(TransitionError):
        transition(session, cr, Status.COMMITTEE_REVIEW, "po")


def test_us11_quorum_required(session):
    members, po = _users(session)
    cr = _case(session, po)
    _vote(session, cr, members[0], "APPROVE")
    _vote(session, cr, members[1], "APPROVE")
    with pytest.raises(TransitionError, match="quorum"):
        record_decision(session, cr, members[0], WF)
    _vote(session, cr, members[2], "REJECT")
    d = record_decision(session, cr, members[0], WF)
    assert d.outcome == "APPROVED" and cr.status == "APPROVED"


def test_us11_tie_defers(session):
    members, po = _users(session)
    cr = _case(session, po)
    for m, v in zip(members, ["APPROVE", "APPROVE", "REJECT", "REJECT"], strict=True):
        _vote(session, cr, m, v)
    assert record_decision(session, cr, members[0], {"quorum": 3, "tie_outcome": "DEFERRED"}).outcome == "DEFERRED"


def test_us10_conflicted_votes_do_not_count(session):
    members, po = _users(session)
    cr = _case(session, po)
    _vote(session, cr, members[0], "APPROVE")
    _vote(session, cr, members[1], "APPROVE")
    _vote(session, cr, members[2], "APPROVE", conflict=True)
    with pytest.raises(TransitionError, match="quorum"):
        record_decision(session, cr, members[0], WF)


def test_non_committee_cannot_decide(session):
    members, po = _users(session)
    cr = _case(session, po)
    for m in members[:3]:
        _vote(session, cr, m, "APPROVE")
    with pytest.raises(TransitionError):
        record_decision(session, cr, po, WF)


def test_conditions_collected(session):
    members, po = _users(session)
    cr = _case(session, po)
    for m in members[:3]:
        _vote(session, cr, m, "APPROVE_WITH_CONDITIONS", conditions=["Limit 10k/day for 90 days"])
    d = record_decision(session, cr, members[0], WF)
    assert d.outcome == "APPROVED_WITH_CONDITIONS"
    assert d.conditions == ["Limit 10k/day for 90 days"]
