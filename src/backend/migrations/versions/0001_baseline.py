"""Baseline schema: all tables, audit append-only triggers, pgvector extension.

Revision ID: 0001_baseline
"""

from alembic import op
from sqlalchemy import text

from raw import models  # noqa: F401
from raw.db import Base, install_audit_triggers

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(conn)
    install_audit_triggers(conn)


def downgrade() -> None:
    raise RuntimeError("the baseline holds the audit trail and is never downgraded")
