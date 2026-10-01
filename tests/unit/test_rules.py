from raw.config_store import control_library, seed_config
from raw.scoring.rules import evaluate_rules, geo_categories, map_controls

CFG = seed_config()

BASE = {
    "customer_types": [], "geographies": [], "channels": [], "third_parties": [], "third_party_roles": [],
    "cross_border": False, "cash": False, "crypto": False, "instant_payments": False,
    "anonymous_or_prepaid": False, "monthly_value_usd": None, "monthly_volume": None, "proposed_controls": [],
}


def facts(**kw):
    return {**BASE, **kw}


def test_sanctioned_geography_is_maximum():
    out = evaluate_rules(facts(geographies=["Avalon", "Drakmoor"]), CFG)
    assert (out["GEO"].likelihood, out["GEO"].impact) == (5, 5)
    assert "GEO-01" in out["GEO"].rule_ids
    assert "SANCTIONS" in out["GEO"].risk_types


def test_domestic_only_is_low():
    out = evaluate_rules(facts(geographies=["Avalon"]), CFG)
    assert out["GEO"].rule_ids == ["GEO-05"]


def test_conservative_combination_takes_max():
    out = evaluate_rules(facts(cross_border=True, crypto=True), CFG)
    assert (out["PRD"].likelihood, out["PRD"].impact) == (5, 5)
    assert set(out["PRD"].rule_ids) == {"PRD-01", "PRD-03"}


def test_unknown_geography_is_unmapped_for_ai():
    out = evaluate_rules(facts(geographies=["Atlantis"]), CFG)
    assert "GEO" not in out
    assert geo_categories(["Atlantis"], CFG["jurisdictions"]) == {"unlisted"}


def test_missing_value_leaves_trx_unmapped():
    out = evaluate_rules(facts(), CFG)
    assert "TRX" not in out
    assert out["PRD"].rule_ids == ["PRD-05"]
    assert out["TPV"].rule_ids == ["TPV-05"]


def test_value_thresholds():
    assert evaluate_rules(facts(monthly_value_usd=60_000_000), CFG)["TRX"].likelihood == 5
    assert evaluate_rules(facts(monthly_value_usd=500_000), CFG)["TRX"].rule_ids == ["TRX-04"]


def test_every_rule_cites_a_policy_chunk_id():
    for r in CFG["rules"]:
        assert r["cite"], r["id"]


def test_control_mapping_by_keyword():
    hits = map_controls(["We use eKYC with liveness", "daily velocity limit of 5k"], control_library())
    assert {c["id"] for c, _ in hits} == {"C-KYC-01", "C-LIM-01"}
