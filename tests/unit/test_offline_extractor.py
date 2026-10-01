from pathlib import Path

import yaml

from raw.config_store import seed_config
from raw.domain import IntakeExtraction, plain
from raw.llm.offline import extract

GOLDEN = yaml.safe_load((Path(__file__).resolve().parents[2] / "evals/datasets/golden_v1.yaml").read_text())["cases"]
CASES = {c["id"]: c for c in GOLDEN}


def run(case_id):
    c = CASES[case_id]
    out = extract(f"{c['title']}. {c['description']}\n{c['document']}", seed_config()["jurisdictions"])
    IntakeExtraction.model_validate(out)
    return plain(out)


def test_gig_payout_case():
    f = run("G01")
    assert set(f["geographies"]) == {"Avalon", "Veridia", "Brightland"}
    assert f["instant_payments"] and f["cross_border"] and not f["crypto"]
    assert f["monthly_value_usd"] == 25_000_000
    assert "payments_processing" in f["third_party_roles"]


def test_real_time_screening_is_not_instant_payment():
    assert run("G04")["instant_payments"] is False


def test_negated_third_parties_not_extracted():
    assert run("G03")["third_party_roles"] == []
