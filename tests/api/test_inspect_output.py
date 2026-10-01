import json
import os

import pytest

from tests.api.test_lifecycle import client, login, to_analyst  # noqa: F401


@pytest.mark.skipif(not os.environ.get("RAW_INSPECT"), reason="manual inspection helper")
def test_dump_case(client):  # noqa: F811
    po = login(client, "priya")
    case = to_analyst(client, po, os.environ.get("RAW_CASE", "G01"))
    a = case["assessment"]
    print(json.dumps({
        "warnings": case["warnings"],
        "extraction": {k: v["value"] for k, v in case["extraction"]["data"].items()},
        "factors": [(f["dimension"], f["likelihood"], f["impact"], f["origin"], f["rule_ids"], f["residual"]) for f in a["factors"]],
        "controls": [c["control_id"] for c in a["controls"]],
        "overall": (a["inherent"], a["inherent_tier"], a["residual"], a["residual_tier"]),
        "steps": a["steps"],
        "narrative": a["narrative"],
        "critique": [(c["status"], c["reason"], c["text"][:90]) for c in a["critique"]["claims"]],
        "usage": case["ai_usage"],
    }, indent=1))
