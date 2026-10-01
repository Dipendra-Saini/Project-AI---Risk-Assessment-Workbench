"""Runtime-harness behaviour with a scripted LLM: critic -> redraft loop, provider fallback, ledger."""

import json
import re

import pytest

from raw.llm.providers import Completion, ProviderError
from raw.models import LLMCall
from tests.api.test_lifecycle import client, login, to_analyst  # noqa: F401

SCORE_RX = re.compile(r"^(PRD|CUS|GEO|CHN|TRX|TPV) [^:]+: likelihood (\d) impact (\d)", re.M)


class ScriptedLLM:
    """Drafts a wrong GEO rating first; fixes it when the critic's feedback arrives."""

    def __init__(self, name):
        self.name, self.model = name, f"{name}-scripted"
        self.draft_prompts: list[str] = []

    def complete(self, system, user, max_tokens, temperature):
        if "draft a financial crime risk assessment" in system:
            self.draft_prompts.append(user)
            wrong = len(self.draft_prompts) == 1
            sections = []
            for dim, lik, imp in SCORE_RX.findall(user):
                if wrong and dim == "GEO":
                    lik, imp = "1", "1"
                sections.append({"dimension": dim, "text": f"{dim} risk is rated likelihood {lik} and impact {imp}. "
                                                           f"[chunk:AML-POL-7.1]"})
            body = {"summary": "Scores are deterministic. [chunk:NPA-POL-2.1]", "sections": sections,
                    "suggested_conditions": ["90-day post-launch review"]}
            return Completion(json.dumps(body), 900, 300)
        if "grounding checker" in system:
            idx = [int(i) for i in re.findall(r"^(\d+)\. CLAIM", user, re.M)]
            return Completion(json.dumps({"verdicts": [{"index": i, "supported": True, "reason": "ok"} for i in idx]}), 200, 40)
        raise ProviderError(f"{self.name} 400 not scripted for this prompt", transient=False)


@pytest.fixture()
def scripted(monkeypatch):
    from raw.llm import router as router_mod
    from raw.settings import get_settings

    monkeypatch.setenv("LLM_MODE", "live")
    get_settings.cache_clear()
    router_mod.BREAKER.failures.clear()
    router_mod.BREAKER.opened.clear()
    llm = ScriptedLLM("gemini")
    monkeypatch.setattr(router_mod, "configured_providers", lambda: {"gemini": llm})
    yield llm
    get_settings.cache_clear()


def test_critic_catches_wrong_rating_and_drafter_fixes_it(scripted, client):  # noqa: F811
    po = login(client, "priya")
    case = to_analyst(client, po, "G04")
    a = case["assessment"]

    assert len(scripted.draft_prompts) == 2, "critic should trigger exactly one redraft"
    assert "rating mismatch" in scripted.draft_prompts[1]
    assert a["narrative_provider"] == "gemini"
    assert a["critique"]["unsupported"] == 0
    geo = next(s for s in a["narrative"]["sections"] if s["dimension"] == "GEO")
    f = next(f for f in a["factors"] if f["dimension"] == "GEO")
    assert f"likelihood {f['likelihood']} and impact {f['impact']}" in geo["text"]

    from raw.db import SessionLocal

    s = SessionLocal()
    calls = s.query(LLMCall).filter(LLMCall.cr_id == case["id"]).all()
    s.close()
    by = {(c.node, c.status) for c in calls}
    assert ("extract_documents", "fallback") in by, "unscripted extraction must degrade to deterministic"
    assert ("draft_assessment", "ok") in by
    assert sum(c.input_tokens for c in calls if c.node == "draft_assessment") == 1800
    assert any("fallback" in w for w in case["extraction"]["flags"])
