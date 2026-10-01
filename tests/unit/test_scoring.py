import copy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from raw.config_store import seed_config
from raw.domain import DIMENSIONS
from raw.scoring.engine import ConfigError, ControlInput, FactorInput, score, tier_for

CFG = seed_config()["scoring"]

ratings = st.integers(min_value=1, max_value=5)
eff = st.floats(min_value=0, max_value=1, allow_nan=False)


@st.composite
def factor_sets(draw):
    dims = draw(st.lists(st.sampled_from(DIMENSIONS), min_size=1, max_size=6, unique=True))
    return [FactorInput(d, draw(ratings), draw(ratings)) for d in dims]


@st.composite
def control_sets(draw):
    n = draw(st.integers(min_value=0, max_value=8))
    return [
        ControlInput(f"C{i}", tuple(draw(st.lists(st.sampled_from(DIMENSIONS), min_size=1, max_size=3, unique=True))),
                     draw(eff), draw(eff))
        for i in range(n)
    ]


@settings(max_examples=300)
@given(factor_sets(), control_sets())
def test_controls_never_eliminate_risk(factors, controls):
    """Brief constraint: controls mitigate risk, they never eliminate it."""
    r = score(factors, controls, CFG)
    for d in r.dimensions.values():
        assert 0 < d.residual <= d.inherent
        assert d.residual >= round(CFG["residual_floor_ratio"] * d.inherent, 2) - 0.01
        assert d.mitigation <= CFG["mitigation_cap"]
    assert 0 < r.residual_overall <= r.inherent_overall


@settings(max_examples=200)
@given(factor_sets(), control_sets())
def test_adding_a_control_never_increases_residual(factors, controls):
    base = score(factors, controls, CFG)
    more = score(factors, [*controls, ControlInput("EXTRA", tuple(DIMENSIONS), 0.9, 0.9)], CFG)
    assert more.residual_overall <= base.residual_overall + 1e-9


@given(factor_sets(), control_sets())
def test_scoring_is_deterministic(factors, controls):
    assert score(factors, controls, CFG).to_trace() == score(factors, controls, CFG).to_trace()


def test_single_critical_dimension_is_not_averaged_away():
    factors = [FactorInput("GEO", 5, 5)] + [FactorInput(d, 1, 1) for d in DIMENSIONS if d != "GEO"]
    r = score(factors, [], CFG)
    assert r.inherent_weighted_mean < 12
    assert r.inherent_overall == pytest.approx(0.8 * 25)
    assert r.inherent_tier == "Critical"


def test_known_example_matches_hand_calculation():
    r = score([FactorInput("TRX", 4, 4)], [ControlInput("C-LIM-01", ("TRX",), 0.8, 0.9)], CFG)
    d = r.dimensions["TRX"]
    assert d.inherent == 16
    assert d.combined_effectiveness == pytest.approx(0.72)
    assert d.mitigation == pytest.approx(0.504, abs=0.01)
    assert d.residual == pytest.approx(16 * (1 - 0.72 * 0.7), abs=0.01)


def test_cap_of_one_is_rejected():
    cfg = copy.deepcopy(CFG)
    cfg["mitigation_cap"] = 1.0
    with pytest.raises(ConfigError):
        score([FactorInput("GEO", 3, 3)], [], cfg)


def test_out_of_range_rating_rejected():
    with pytest.raises(ConfigError):
        score([FactorInput("GEO", 6, 3)], [], CFG)


@pytest.mark.parametrize(
    "value,tier", [(0, "Low"), (5.99, "Low"), (6, "Medium"), (12, "High"), (18, "Critical"), (25, "Critical")]
)
def test_tier_boundaries(value, tier):
    assert tier_for(value, CFG["tiers"]) == tier
