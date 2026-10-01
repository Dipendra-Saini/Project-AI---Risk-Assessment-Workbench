"""Append-only, hash-chained audit log (ADR-005)."""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from raw.models import AuditEvent

GENESIS = "0" * 64


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def compute_hash(prev_hash: str, event: dict[str, Any]) -> str:
    return hashlib.sha256((prev_hash + _canonical(event)).encode()).hexdigest()


def _event_body(e: AuditEvent) -> dict[str, Any]:
    return {
        "seq": e.seq,
        "ts": e.ts,
        "actor": e.actor,
        "action": e.action,
        "entity_type": e.entity_type,
        "entity_id": e.entity_id,
        "payload": e.payload,
    }


def record(
    session: Session,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: Any,
    payload: dict[str, Any] | None = None,
) -> AuditEvent:
    """The only way to write an audit event."""
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        session.execute(text("SELECT pg_advisory_xact_lock(424242)"))
    session.flush()
    last = session.execute(select(AuditEvent).order_by(AuditEvent.seq.desc()).limit(1)).scalar_one_or_none()
    seq = (last.seq + 1) if last else 1
    prev_hash = last.hash if last else GENESIS
    event = AuditEvent(
        seq=seq,
        ts=datetime.now(UTC).isoformat(),
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        payload=json.loads(_canonical(payload or {})),
        prev_hash=prev_hash,
        hash="",
    )
    event.hash = compute_hash(prev_hash, _event_body(event))
    session.add(event)
    session.flush()
    return event


def verify(session: Session) -> dict[str, Any]:
    prev = GENESIS
    count = 0
    for e in session.execute(select(AuditEvent).order_by(AuditEvent.seq)).scalars():
        count += 1
        if e.prev_hash != prev or compute_hash(prev, _event_body(e)) != e.hash:
            return {"valid": False, "events": count, "first_broken_seq": e.seq}
        prev = e.hash
    return {"valid": True, "events": count, "head_hash": prev}


def head(session: Session) -> dict[str, Any]:
    n = session.execute(select(func.max(AuditEvent.seq))).scalar()
    if not n:
        return {"seq": 0, "hash": GENESIS}
    e = session.get(AuditEvent, n)
    return {"seq": e.seq, "hash": e.hash}
