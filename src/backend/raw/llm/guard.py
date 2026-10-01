"""Deterministic screens for untrusted uploaded text and for extracted evidence."""

import re

INJECTION_PATTERNS = [
    r"ignore (all |any )?(previous|prior|above) (instructions|prompts?)",
    r"disregard (the )?(system|previous) (prompt|instructions)",
    r"you are now",
    r"(rate|score|mark) (all|every|the) risks? (as )?(low|zero|minimal)",
    r"note to the ai",
    r"system prompt",
    r"should be approved",
    r"do not (flag|report|escalate)",
]
_INJ = [re.compile(p, re.I) for p in INJECTION_PATTERNS]


def screen_injection(text: str) -> list[str]:
    hits = []
    for rx in _INJ:
        m = rx.search(text)
        if m:
            hits.append(m.group(0))
    return hits


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def span_in_source(span: str, source: str) -> bool:
    if not span:
        return False
    return _norm(span) in _norm(source)
