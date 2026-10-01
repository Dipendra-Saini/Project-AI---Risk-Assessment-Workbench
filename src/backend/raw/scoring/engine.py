"""Deterministic risk scoring (ADR-001). Pure functions, no I/O.

inherent_d   = likelihood x impact                          (1..25)
e_c          = design x operating                           (0..1)
combined_d   = 1 - prod(1 - e_c) over controls mapped to d
mitigation_d = combined_d x mitigation_cap                  (cap < 1)
residual_d   = max(inherent_d x (1 - mitigation_d), residual_floor_ratio x inherent_d)
overall      = max(weighted_mean_d, max_dimension_floor_ratio x max_d)
"""

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class FactorInput:
    dimension: str
    likelihood: int
    impact: int


@dataclass(frozen=True)
class ControlInput:
    control_id: str
    dims: tuple[str, ...]
    design: float
    operating: float


@dataclass
class DimensionScore:
    dimension: str
    likelihood: int
    impact: int
    inherent: float
    controls: list[dict[str, Any]]
    combined_effectiveness: float
    mitigation: float
    residual: float
    floor_applied: bool


@dataclass
class ScoreResult:
    dimensions: dict[str, DimensionScore]
    inherent_weighted_mean: float
    inherent_max: float
    inherent_overall: float
    residual_weighted_mean: float
    residual_max: float
    residual_overall: float
    inherent_tier: str
    residual_tier: str
    config_hash: str
    steps: list[str] = field(default_factory=list)

    def to_trace(self) -> dict[str, Any]:
        d = asdict(self)
        d["dimensions"] = {k: asdict(v) for k, v in self.dimensions.items()}
        return d


def config_hash(scoring_cfg: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(scoring_cfg, sort_keys=True).encode()).hexdigest()[:16]


def validate_config(cfg: dict[str, Any]) -> None:
    cap = cfg["mitigation_cap"]
    floor = cfg["residual_floor_ratio"]
    dim_floor = cfg["max_dimension_floor_ratio"]
    if not 0 <= cap < 1:
        raise ConfigError("mitigation_cap must be in [0, 1): controls never eliminate risk")
    if not 0 < floor <= 1:
        raise ConfigError("residual_floor_ratio must be in (0, 1]")
    if not 0 <= dim_floor <= 1:
        raise ConfigError("max_dimension_floor_ratio must be in [0, 1]")
    weights = [d["weight"] for d in cfg["dimensions"].values()]
    if any(w < 0 for w in weights) or sum(weights) <= 0:
        raise ConfigError("dimension weights must be >= 0 and sum to > 0")
    mins = [t["min"] for t in cfg["tiers"]]
    if mins != sorted(mins) or mins[0] != 0:
        raise ConfigError("tiers must be ascending and start at 0")


def tier_for(score: float, tiers: list[dict[str, Any]]) -> str:
    name = tiers[0]["name"]
    for t in tiers:
        if score >= t["min"]:
            name = t["name"]
    return name


def _r(x: float) -> float:
    return round(x, 2)


def score(factors: list[FactorInput], controls: list[ControlInput], cfg: dict[str, Any]) -> ScoreResult:
    validate_config(cfg)
    dims_cfg = cfg["dimensions"]
    cap = cfg["mitigation_cap"]
    floor = cfg["residual_floor_ratio"]
    steps: list[str] = []
    by_dim: dict[str, DimensionScore] = {}

    for f in factors:
        if f.dimension not in dims_cfg:
            raise ConfigError(f"unknown dimension {f.dimension}")
        if not (1 <= f.likelihood <= 5 and 1 <= f.impact <= 5):
            raise ConfigError(f"{f.dimension}: likelihood and impact must be 1-5")
        inherent = float(f.likelihood * f.impact)
        applied = []
        remaining = 1.0
        for c in controls:
            if f.dimension in c.dims:
                e = max(0.0, min(1.0, c.design)) * max(0.0, min(1.0, c.operating))
                remaining *= 1 - e
                applied.append({"control_id": c.control_id, "effectiveness": _r(e)})
        combined = 1 - remaining
        mitigation = combined * cap
        raw_residual = inherent * (1 - mitigation)
        floor_value = floor * inherent
        residual = max(raw_residual, floor_value)
        by_dim[f.dimension] = DimensionScore(
            dimension=f.dimension,
            likelihood=f.likelihood,
            impact=f.impact,
            inherent=_r(inherent),
            controls=applied,
            combined_effectiveness=_r(combined),
            mitigation=_r(mitigation),
            residual=_r(residual),
            floor_applied=residual == floor_value and floor_value > raw_residual,
        )
        steps.append(
            f"{f.dimension}: inherent {f.likelihood}x{f.impact}={inherent:g}; "
            f"controls {len(applied)} combined e={combined:.2f}; mitigation {mitigation:.2f} (cap {cap}); "
            f"residual {residual:.2f}"
        )

    if not by_dim:
        raise ConfigError("at least one dimension must be rated")

    total_w = sum(dims_cfg[d]["weight"] for d in by_dim) or 1.0

    def overall(attr: str) -> tuple[float, float, float]:
        mean = sum(getattr(s, attr) * dims_cfg[d]["weight"] for d, s in by_dim.items()) / total_w
        mx = max(getattr(s, attr) for s in by_dim.values())
        return mean, mx, max(mean, cfg["max_dimension_floor_ratio"] * mx)

    i_mean, i_max, i_overall = overall("inherent")
    r_mean, r_max, r_overall = overall("residual")
    ratio = cfg["max_dimension_floor_ratio"]
    steps.append(f"overall inherent = max(weighted mean {i_mean:.2f}, {ratio} x max {i_max:g}) = {i_overall:.2f}")
    steps.append(f"overall residual = max(weighted mean {r_mean:.2f}, {ratio} x max {r_max:.2f}) = {r_overall:.2f}")

    return ScoreResult(
        dimensions=by_dim,
        inherent_weighted_mean=_r(i_mean),
        inherent_max=_r(i_max),
        inherent_overall=_r(i_overall),
        residual_weighted_mean=_r(r_mean),
        residual_max=_r(r_max),
        residual_overall=_r(r_overall),
        inherent_tier=tier_for(i_overall, cfg["tiers"]),
        residual_tier=tier_for(r_overall, cfg["tiers"]),
        config_hash=config_hash(cfg),
        steps=steps,
    )
