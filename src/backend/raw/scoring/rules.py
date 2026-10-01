"""Deterministic factor rule engine and control mapper. Pure functions."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuleOutcome:
    dimension: str
    likelihood: int
    impact: int
    rule_ids: list[str] = field(default_factory=list)
    risk_types: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def rationale(self) -> str:
        return "; ".join(f"{rid}: {note}" for rid, note in zip(self.rule_ids, self.notes, strict=False))


def geo_categories(geographies: list[str], jurisdictions: dict[str, list[str]]) -> set[str]:
    lookup = {name.lower(): cat for cat, names in jurisdictions.items() for name in names}
    cats = {lookup.get(g.strip().lower(), "unlisted") for g in geographies if g and g.strip()}
    if cats and cats <= {"domestic"}:
        return {"domestic_only"}
    return cats - {"domestic"}


def _matches(when: dict[str, Any], facts: dict[str, Any], geo_cats: set[str]) -> bool:
    for key, expected in when.items():
        if key == "geo_category":
            if expected not in geo_cats:
                return False
        elif key == "flag":
            if facts.get(expected) is not True:
                return False
        elif key == "no_flags":
            if any(facts.get(f) is not False for f in expected):
                return False
        elif key == "customer_type":
            if expected not in (facts.get("customer_types") or []):
                return False
        elif key == "channel":
            if expected not in (facts.get("channels") or []):
                return False
        elif key == "third_party_role":
            if expected not in (facts.get("third_party_roles") or []):
                return False
        elif key == "no_third_parties":
            if facts.get("third_parties") or facts.get("third_party_roles"):
                return False
        elif key == "monthly_value_usd_gte":
            v = facts.get("monthly_value_usd")
            if v is None or v < expected:
                return False
        elif key == "monthly_value_usd_lt":
            v = facts.get("monthly_value_usd")
            if v is None or v >= expected:
                return False
        else:
            raise ValueError(f"unknown rule condition {key}")
    return True


def evaluate_rules(facts: dict[str, Any], config: dict[str, Any]) -> dict[str, RuleOutcome]:
    """Return outcomes for dimensions where at least one rule fired.

    Conservative combination: the highest likelihood and highest impact among
    fired rules win. Dimensions absent from the result are 'unmapped' and go to
    the AI suggester (then human confirmation at G1).
    """
    geo_cats = geo_categories(facts.get("geographies") or [], config["jurisdictions"])
    out: dict[str, RuleOutcome] = {}
    for rule in config["rules"]:
        if not _matches(rule["when"], facts, geo_cats):
            continue
        dim = rule["dim"]
        o = out.get(dim)
        if o is None:
            o = out[dim] = RuleOutcome(dimension=dim, likelihood=rule["likelihood"], impact=rule["impact"])
        else:
            o.likelihood = max(o.likelihood, rule["likelihood"])
            o.impact = max(o.impact, rule["impact"])
        o.rule_ids.append(rule["id"])
        o.notes.append(rule.get("note", ""))
        for rt in rule.get("risk_types", []):
            if rt not in o.risk_types:
                o.risk_types.append(rt)
        if rule.get("cite") and rule["cite"] not in o.citations:
            o.citations.append(rule["cite"])
    return out


def map_controls(proposed: list[str], library: list[dict[str, Any]]) -> list[tuple[dict[str, Any], str]]:
    """Link free-text controls named in a submission to the control library."""
    text = " | ".join(proposed or []).lower()
    hits = []
    for c in library:
        for kw in c.get("keywords", []):
            if kw.lower() in text:
                hits.append((c, kw))
                break
    return hits
