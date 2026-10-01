"""Idempotent reference data: config v1, control library, policy corpus, demo users."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from raw import config_store
from raw.api.deps import hash_password
from raw.audit import chain
from raw.models import Control, PolicyChunk, User
from raw.rag.ingest import ingest

DEMO_USERS = [
    ("priya", "Priya Sharma", "product_owner"),
    ("omar", "Omar Haddad", "product_owner"),
    ("arjun", "Arjun Mehta", "analyst"),
    ("sara", "Sara Lindqvist", "analyst"),
    ("meera", "Meera Iyer (Chair)", "committee"),
    ("dev", "Dev Patel", "committee"),
    ("lina", "Lina Okafor", "committee"),
    ("kofi", "Kofi Mensah", "committee"),
]
DEMO_PASSWORD = "demo"


def ensure_reference_data(session: Session) -> None:
    config_store.active(session)
    if not session.execute(select(func.count(Control.id))).scalar():
        for c in config_store.control_library():
            session.add(Control(id=c["id"], name=c["name"], dims=c["dims"], design=c["design"], operating=c["operating"],
                                keywords=c.get("keywords", [])))
        session.flush()
        chain.record(session, "system", "controls.seeded", "control_library", "v1", {"count": len(config_store.control_library())})
    if not session.execute(select(func.count(PolicyChunk.id))).scalar():
        ingest(session)
    if not session.execute(select(func.count(User.id))).scalar():
        for username, name, role in DEMO_USERS:
            session.add(User(username=username, name=name, role=role, password_hash=hash_password(DEMO_PASSWORD)))
        session.flush()
        chain.record(session, "system", "users.seeded", "user", "demo", {"count": len(DEMO_USERS)})
