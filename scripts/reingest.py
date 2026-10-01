"""Re-ingest the policy corpus after editing data/policies/*.md.

    PYTHONPATH=src/backend .venv/bin/python scripts/reingest.py

Startup only ingests into an empty corpus. This re-embeds chunks whose text or
embedding model changed, adds new ones, and records a `policy.ingested` audit event.
"""

from raw.db import init_db, session_scope
from raw.rag.ingest import ingest


def main() -> None:
    init_db()
    with session_scope() as s:
        print(ingest(s))


if __name__ == "__main__":
    main()
