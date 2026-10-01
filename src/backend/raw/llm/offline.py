"""Deterministic 'offline provider'.

Used when no free-tier key is configured, when providers fail, when the token
budget is exhausted, and as the rules baseline in evals. Outputs always pass the
same Pydantic schemas as LLM outputs, and are flagged origin="offline".
"""

import re
from typing import Any

from raw.domain import ChangeType

CUSTOMER_KW = {
    "pep": ["politically exposed", " pep", "peps"],
    "msb": ["money services", " msb", "msbs", "e-money", "payment institution", "remittance compan"],
    "non_resident": ["non-resident", "nonresident", "non resident"],
    "nonprofit": ["non-profit", "nonprofit", "charit"],
    "high_net_worth": ["high-net-worth", "high net worth", "wealth clients"],
    "corporate": ["corporate", "legal entit", "importers"],
    "small_business": ["small business"],
    "retail": ["retail", "consumer", "individual", "cardholder", "students", "members", "workers", "customers aged",
               "employees"],
}
# Phrases whose words would otherwise trigger a broader customer type: the HNW segment is not also
# "retail", and "corporate payments/cards" names a product, not a customer segment.
CUSTOMER_SCRUB = re.compile(r"(?<=high-net-worth) individuals|(?<=high net worth) individuals|"
                            r"\bcorporate (?=(payments|cards?|banking|treasury|account))", re.I)
CHANNEL_KW = {
    "branch": ["branch", "face to face", "face-to-face"],
    "online": ["online", "website", "internet banking", "web "],
    "mobile": ["mobile app", "mobile", " the app", " app "],
    "api": [" api", "embedded finance", "banking-as-a-service"],
    "agent": ["agent", "intermediar", "broker"],
    "phone": ["by phone", "phone contact", "contact centre", "call centre", "call center", "telephone"],
}
VENDOR_CUES = ["partner", "vendor", "outsourc", "third-party", "third party", "operated by", "custodian", "processor",
               "acts as", "provider"]
ROLE_KW = {
    "kyc": ["kyc", "document review", "identity check"],
    "transaction_monitoring": ["transaction monitoring", "payment screening", "monitoring and"],
    "payments_processing": ["payment processor", "processor", "processing"],
    "custody": ["custod"],
    "marketing": ["market"],
    "it_hosting": ["hosting", "data centre", "data center"],
}
FLAG_RX = {
    "cross_border": re.compile(r"cross[- ]border|abroad|international transfer|overseas", re.I),
    "cash": re.compile(r"\bcash\b", re.I),
    "crypto": re.compile(r"crypto|bitcoin|\bether\b|virtual asset|tokeni[sz]ed|blockchain", re.I),
    "instant_payments": re.compile(
        r"\binstant(ly)?\b|settle[s]? in seconds|real[- ]time (?:payment|payout|transfer|settlement)s?", re.I),
    "anonymous_or_prepaid": re.compile(r"prepaid|stored[- ]value|gift card|anonymous", re.I),
}
NEGATION = re.compile(r"\b(no|not|without|never)\b[^.]{0,40}$", re.I)
VALUE_RX = re.compile(r"USD\s?([\d][\d,]*(?:\.\d+)?)\s*(million|billion|m\b|bn\b)?", re.I)
VOLUME_RX = re.compile(r"([\d][\d,]*)\s+(payouts|payments|transactions|transfers)", re.I)
NAME_RX = re.compile(r"(?:partner|vendor|custodian|by|to|with)\s+((?:[A-Z][\w&]+\s?){1,3})")
CHANGE_KW = [
    (ChangeType.VENDOR_ONBOARDING, ["outsourc", "vendor", "data centre", "hosting"]),
    (ChangeType.NEW_GEOGRAPHY, ["new market", "expand to", "extend", "enter"]),
    (ChangeType.NEW_CUSTOMER_SEGMENT, ["segment", "onboard", "open accounts"]),
    (ChangeType.PROCESS_CHANGE, ["process change", "replace", "process"]),
    (ChangeType.FEATURE_CHANGE, ["feature"]),
    (ChangeType.NEW_PRODUCT, ["launch", "new product", "offer", "propose"]),
]


def sentences(text: str) -> list[str]:
    """Split on sentence ends and blank lines; single line-wraps stay inside a sentence."""
    paragraphs = re.split(r"\n\s*\n|\n(?=\[)", text)
    out = []
    for para in paragraphs:
        joined = re.sub(r"\s*\n\s*", " ", para)
        out += [p.strip() for p in re.split(r"(?<=[.!?])\s+", joined) if p.strip()]
    return out


def _first_hit(sents: list[str], kws: list[str]) -> str | None:
    for s in sents:
        low = f" {s.lower()} "
        for kw in kws:
            i = low.find(kw)
            if i >= 0 and not NEGATION.search(low[:i]):
                return s
    return None


def _field(value: Any, span: str | None, conf: float) -> dict[str, Any]:
    return {"value": value, "confidence": conf if span else 0.3, "source_span": (span or "")[:160], "origin": "offline"}


def extract(text: str, jurisdictions: dict[str, list[str]]) -> dict[str, Any]:
    sents = sentences(text)
    out: dict[str, Any] = {}

    found, spans = [], []
    customer_sents = [CUSTOMER_SCRUB.sub(" ", s) for s in sents]
    for ctype, kws in CUSTOMER_KW.items():
        s = _first_hit(customer_sents, kws)
        if s:
            found.append(ctype)
            spans.append(s)
    out["customer_types"] = _field(found, spans[0] if spans else None, 0.6)

    all_names = [n for names in jurisdictions.values() for n in names]
    geos = [n for n in all_names if re.search(rf"\b{re.escape(n)}\b", text)]
    geo_span = next((s for s in sents if any(g in s for g in geos)), None)
    out["geographies"] = _field(geos, geo_span, 0.8)

    found, spans = [], []
    for ch, kws in CHANNEL_KW.items():
        s = _first_hit(sents, kws)
        if s:
            found.append(ch)
            spans.append(s)
    out["channels"] = _field(found, spans[0] if spans else None, 0.55)

    vendor_sents = [s for s in sents if any(c in s.lower() for c in VENDOR_CUES) and not s.lower().startswith("controls")]
    roles, role_span = [], None
    for role, kws in ROLE_KW.items():
        s = _first_hit(vendor_sents, kws)
        if s:
            roles.append(role)
            role_span = role_span or s
    names: list[str] = []
    for s in vendor_sents:
        for m in NAME_RX.finditer(s):
            name = m.group(1).strip()
            if name not in all_names and name.split()[0] not in {"The", "Our", "We", "USD"} and name not in names:
                names.append(name)
    out["third_parties"] = _field(names, vendor_sents[0] if names else None, 0.5)
    out["third_party_roles"] = _field(roles, role_span, 0.5)

    foreign = [g for g in geos if g not in jurisdictions.get("domestic", [])]
    for flag, rx in FLAG_RX.items():
        s = next((x for x in sents if rx.search(x) and not NEGATION.search(x[: rx.search(x).start()])), None)
        val = bool(s)
        if flag == "cross_border" and not val and foreign:
            val, s = True, geo_span
        out[flag] = _field(val, s, 0.6)

    value, vspan = None, None
    for s in sents:
        m = VALUE_RX.search(s)
        if m and ("month" in s.lower() or "per" in s.lower()):
            n = float(m.group(1).replace(",", ""))
            unit = (m.group(2) or "").lower()
            n *= 1e9 if unit in {"billion", "bn"} else 1e6 if unit in {"million", "m"} else 1
            value, vspan = n, s
            break
    out["monthly_value_usd"] = _field(value, vspan, 0.7)

    vol, volspan = None, None
    for s in sents:
        m = VOLUME_RX.search(s)
        if m:
            vol, volspan = int(m.group(1).replace(",", "")), s
            break
    out["monthly_volume"] = _field(vol, volspan, 0.5)

    controls, cspan = [], None
    for s in sents:
        low = s.lower()
        if low.startswith(("controls", "mitigation", "control:")):
            body = s.split(":", 1)[1] if ":" in s else s
            controls += [re.sub(r"^and\s+", "", c.strip(" .")) for c in re.split(r",(?!\d{3})|;", body) if c.strip(" .")]
            cspan = cspan or s
    if any(c.lower().startswith("no controls") for c in controls):
        controls = []
    out["proposed_controls"] = _field(controls, cspan, 0.6)
    return out


def classify(text: str) -> dict[str, Any]:
    low = text.lower()
    for ctype, kws in CHANGE_KW:
        if any(k in low for k in kws):
            return {"change_type": ctype.value, "confidence": 0.4}
    return {"change_type": ChangeType.OTHER.value, "confidence": 0.2}


def suggest_factor(dimension: str, default: dict[str, int], citations: list[str]) -> dict[str, Any]:
    return {
        "likelihood": default["likelihood"],
        "impact": default["impact"],
        "rationale": "No deterministic rule matched this dimension; a default moderate rating is applied pending "
                     "analyst judgement.",
        "citations": citations[:1],
    }


def first_sentence(text: str) -> str:
    s = sentences(text)
    return s[0] if s else text


def draft(dim_rows: list[dict[str, Any]], chunks: dict[str, Any], overall: dict[str, Any], facts: dict[str, Any]) -> dict:
    sections = []
    conditions = []
    for d in dim_rows:
        cites = [c for c in d["citations"] if c in chunks] or list(chunks)[:1]
        c0 = cites[0]
        text = (f"{d['name']} risk is rated likelihood {d['likelihood']} and impact {d['impact']} "
                f"because {d['rationale'].rstrip('.')}. [chunk:{c0}] ")
        text += f"{first_sentence(chunks[c0]['text'])} [chunk:{c0}] "
        if d["controls"]:
            text += (f"Mapped controls ({', '.join(d['controls'])}) reduce inherent {d['inherent']:g} to residual "
                     f"{d['residual']:g}; controls reduce but never eliminate risk. [chunk:AML-POL-7.1]")
        else:
            text += ("No controls are mapped to this dimension, so residual risk stays close to inherent risk; controls "
                     "reduce but never eliminate risk. [chunk:AML-POL-7.1]")
        sections.append({"dimension": d["dimension"], "text": text.strip()})
        if d["residual"] >= 12:
            conditions.append(f"{d['name']}: evidence of control testing before go-live and a 90-day post-launch review.")
    summary = (f"Overall inherent risk is {overall['inherent']:g} ({overall['inherent_tier']}) and residual risk is "
               f"{overall['residual']:g} ({overall['residual_tier']}) under scoring configuration "
               f"v{overall['config_version']}. [chunk:NPA-POL-2.1]")
    return {"summary": summary, "sections": sections, "suggested_conditions": conditions[:4]}


def critique(claims: list[dict[str, Any]]) -> dict[str, Any]:
    return {"verdicts": [{"index": c["index"], "supported": c["overlap"] >= 0.12,
                          "reason": f"lexical overlap {c['overlap']:.2f}"} for c in claims]}
