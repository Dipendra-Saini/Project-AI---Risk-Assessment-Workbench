"""Turn human corrections into candidate eval cases (the human-in-the-loop -> evals feedback loop).

    PYTHONPATH=src/backend .venv/bin/python scripts/overrides_to_evals.py [--out evals/datasets/candidates.yaml]

Every analyst/PO override is a labelled example of where the AI (or rules) got it wrong.
This exports, per case with at least one override:
  - the submitted document text
  - corrected facts (confirmed extraction after PO edits)
  - the final residual tier after human overrides
  - which fields / factors were corrected and why

Output is a *candidate* file. Nothing is added to the golden set automatically: an FCRM SME
reviews candidates and moves accepted ones into golden_vN.yaml (new dataset version, never edit in place).
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "backend"))

import yaml  # noqa: E402
from sqlalchemy import select  # noqa: E402

from raw.db import session_scope  # noqa: E402
from raw.domain import plain  # noqa: E402
from raw.models import ChangeRequest, Document, Override  # noqa: E402
from raw.services.assessment import latest_assessment, latest_extraction  # noqa: E402

FACT_KEYS = ["customer_types", "geographies", "channels", "third_party_roles", "cross_border", "cash", "crypto",
             "instant_payments", "anonymous_or_prepaid", "monthly_value_usd"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "evals/datasets/candidates_from_overrides.yaml"))
    args = ap.parse_args()

    out = []
    with session_scope() as s:
        by_case = defaultdict(list)
        for o in s.execute(select(Override).order_by(Override.id)).scalars():
            by_case[o.cr_id].append(o)
        for cr_id, overrides in by_case.items():
            cr = s.get(ChangeRequest, cr_id)
            ext = latest_extraction(s, cr_id, confirmed_only=True) or latest_extraction(s, cr_id)
            a = latest_assessment(s, cr_id)
            docs = s.execute(select(Document).where(Document.cr_id == cr_id)).scalars().all()
            facts = plain(ext.data) if ext else {}
            controls = sorted({c.control_id for c in a.controls}) if a else []
            out.append({
                "id": f"OV-{cr.ref}",
                "title": cr.title,
                "change_type": cr.change_type,
                "business_line": cr.business_line,
                "description": cr.description,
                "document": "\n\n".join(d.text or "" for d in docs),
                "expected": {
                    "facts": {k: facts.get(k) for k in FACT_KEYS} | {"controls": controls},
                    "residual_tier": a.residual_tier if a else None,
                },
                "provenance": {
                    "status": cr.status,
                    "corrections": [{"type": o.target_type, "key": o.target_key, "old": o.old_value, "new": o.new_value,
                                     "reason": o.reason, "tier_before": o.tier_before, "tier_after": o.tier_after}
                                    for o in overrides],
                    "review": "PENDING SME REVIEW - do not add to golden set without sign-off",
                },
            })
    Path(args.out).write_text(yaml.safe_dump({"cases": out}, sort_keys=False, allow_unicode=True))
    print(f"{len(out)} candidate case(s) with human corrections -> {args.out}")


if __name__ == "__main__":
    main()
