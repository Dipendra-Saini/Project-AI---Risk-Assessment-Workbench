"""Seed the demo: reference data + golden cases left at different workflow stages.

    PYTHONPATH=src/backend .venv/bin/python scripts/seed.py [--reset]

Runs the real pipeline (offline / replay / live depending on LLM_MODE) through
the same service functions the API uses, so the audit trail is genuine.
"""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "backend"))
os.environ.setdefault("PIPELINE_SYNC", "true")

import yaml  # noqa: E402
from sqlalchemy import select  # noqa: E402

from raw.bootstrap import ensure_reference_data  # noqa: E402
from raw.db import init_db, session_scope  # noqa: E402
from raw.graph import runner  # noqa: E402
from raw.models import ChangeRequest, User  # noqa: E402
from raw.services import cases  # noqa: E402
from raw.services.assessment import latest_assessment  # noqa: E402
from raw.settings import get_settings  # noqa: E402

GOLDEN = {c["id"]: c for c in yaml.safe_load((ROOT / "evals/datasets/golden_v1.yaml").read_text())["cases"]}

# (golden id, owner, target stage)
PLAN = [
    ("G13", "priya", "draft_extracted"),   # sanctioned vendor waiting at G0
    ("G01", "priya", "analyst_review"),    # gig payouts: the main demo case
    ("G17", "omar", "analyst_review"),     # prompt injection flagged
    ("G18", "omar", "analyst_review"),     # incomplete: AI-suggested factors pending G1
    ("G02", "priya", "committee"),         # crypto, awaiting votes (2 of 3 cast)
    ("G03", "omar", "decided"),            # low-risk savings, approved
]


def user(s, name):
    return s.execute(select(User).where(User.username == name)).scalar_one()


def create(gid, owner):
    g = GOLDEN[gid]
    with session_scope() as s:
        cr = cases.create_case(s, user(s, owner), {"title": g["title"], "description": g["description"],
                                                   "change_type": g["change_type"], "business_line": g["business_line"]})
        cases.add_document(s, cr, user(s, owner), f"{gid.lower()}-brief.txt", g["document"].encode(), "text/plain",
                           get_settings().max_upload_bytes)
        return cr.id


def submit(cr_id, owner):
    with session_scope() as s:
        cases.confirm_intake(s, s.get(ChangeRequest, cr_id), user(s, owner))
    runner.resume(cr_id, "confirm")


def sign_and_send(cr_id):
    with session_scope() as s:
        cr = s.get(ChangeRequest, cr_id)
        an = user(s, "arjun")
        a = latest_assessment(s, cr_id)
        for f in a.factors:
            if f.origin in {"ai", "offline"} and not f.confirmed:
                cases.accept_factor(s, cr, an, f.dimension)
        cases.signoff_narrative(s, cr, an, "Seed: narrative reviewed against cited policy sections")
        cases.submit_to_committee(s, cr, an)
    runner.resume(cr_id, "complete")


def vote(cr_id, members, v, rationale, conditions=None):
    with session_scope() as s:
        cr = s.get(ChangeRequest, cr_id)
        for m in members:
            cases.cast_vote(s, cr, user(s, m), v, rationale, False, conditions or [])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="delete the local SQLite databases first")
    args = ap.parse_args()
    settings = get_settings()
    if args.reset and not settings.is_postgres:
        for p in (ROOT / "raw.db", ROOT / "raw_checkpoints.db"):
            for suffix in ("", "-wal", "-shm"):
                Path(str(p) + suffix).unlink(missing_ok=True)
    init_db()
    with session_scope() as s:
        ensure_reference_data(s)
        if s.execute(select(ChangeRequest)).first():
            print("cases already exist; use --reset to reseed")
            return

    for gid, owner, stage in PLAN:
        cr_id = create(gid, owner)
        runner.start(cr_id, "intake")
        if stage == "draft_extracted":
            continue
        submit(cr_id, owner)
        if stage == "analyst_review":
            if gid == "G01":
                with session_scope() as s:
                    o = cases.override_factor(s, s.get(ChangeRequest, cr_id), user(s, "arjun"), "TPV", 4, 5,
                                              "PayRoute Ltd also screens payouts for us; sanctions screening is "
                                              "effectively outsourced, so third-party impact is higher than the rule assumes")
                    print(f"G01 override: tier {o.tier_before} -> {o.tier_after}, second analyst needed: {o.requires_ack}")
            continue
        sign_and_send(cr_id)
        if stage == "committee":
            vote(cr_id, ["meera", "dev"], "APPROVE_WITH_CONDITIONS", "Acceptable only with strict limits and analytics",
                 ["Blockchain analytics alerts reviewed daily for 90 days"])
            continue
        vote(cr_id, ["meera", "dev", "lina"], "APPROVE", "Low residual risk; standard controls sufficient")
        with session_scope() as s:
            cases.decide(s, s.get(ChangeRequest, cr_id), user(s, "meera"))

    with session_scope() as s:
        for cr in s.execute(select(ChangeRequest).order_by(ChangeRequest.id)).scalars():
            a = latest_assessment(s, cr.id)
            print(f"{cr.ref}  {cr.status:<26} {a.residual_tier if a else '-':<9} {cr.title}")
    print("\nLogin at http://localhost:5173 (make web) or :8080 (make up) with any demo user (password: demo):")
    print("  product owners: priya, omar | analysts: arjun, sara | committee: meera, dev, lina, kofi")


if __name__ == "__main__":
    main()
