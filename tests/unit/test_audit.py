import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError

from raw.audit import chain


def test_chain_verifies(session):
    for i in range(5):
        chain.record(session, "tester", "thing.happened", "x", i, {"i": i, "nested": {"a": [1, 2.5]}})
    session.commit()
    result = chain.verify(session)
    assert result["valid"] and result["events"] == 5


def test_update_and_delete_are_blocked(session):
    chain.record(session, "tester", "a", "x", 1, {})
    session.commit()
    with pytest.raises(DatabaseError):
        session.execute(text("UPDATE audit_events SET actor='mallory'"))
    session.rollback()
    with pytest.raises(DatabaseError):
        session.execute(text("DELETE FROM audit_events"))
    session.rollback()


def test_us14_audit_chain_tamper_detected(session):
    for i in range(4):
        chain.record(session, "tester", "a", "x", i, {"score": i})
    session.commit()
    # A rogue DBA drops the trigger and edits history: still detectable.
    session.execute(text("DROP TRIGGER audit_no_update"))
    session.execute(text("UPDATE audit_events SET payload='{\"score\": 99}' WHERE seq=2"))
    session.commit()
    result = chain.verify(session)
    assert result == {"valid": False, "events": 2, "first_broken_seq": 2}
