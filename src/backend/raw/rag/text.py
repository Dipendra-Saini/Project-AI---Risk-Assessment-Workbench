import re

STOPWORDS = frozenset(
    "a an and are as at be by for from has have in is it its of on or that the this to was were will with "
    "we our you your they their which who what when where how not no can may must should into than then "
    "there these those such per also any all each other more most".split()
)

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in STOPWORDS and len(t) > 1]


def estimate_tokens(text: str) -> int:
    """~4 characters per token; used for budgeting before a call."""
    return max(1, len(text) // 4)
