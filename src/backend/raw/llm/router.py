"""Single entry point for every LLM call (ADR-004).

Order of operations for complete_json():
  1. render versioned prompt          5. provider chain by tier (circuit breaker, 1 retry on transient)
  2. cache lookup (DB)                6. JSON parse + Pydantic validation, 1 repair attempt
  3. replay lookup (replay mode)      7. ledger row + metrics + trace span for every outcome
  4. per-case budget check            8. deterministic fallback if everything else fails
"""

import hashlib
import json
import logging
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from raw.llm.prompts import Prompt, load_prompt
from raw.llm.providers import ROUTES, ProviderError, configured_providers
from raw.models import LLMCache, LLMCall
from raw.observability import metrics
from raw.observability.tracing import span
from raw.rag.text import estimate_tokens
from raw.settings import get_settings

log = logging.getLogger(__name__)
M = TypeVar("M", bound=BaseModel)


@dataclass
class LLMResult(Generic[M]):  # noqa: UP046
    data: M
    provider: str
    model: str
    cached: bool
    fallback_reason: str | None
    input_tokens: int
    output_tokens: int

    @property
    def degraded(self) -> bool:
        return self.fallback_reason is not None


class CircuitBreaker:
    def __init__(self, threshold: int = 3, cooldown_s: float = 60):
        self.threshold, self.cooldown_s = threshold, cooldown_s
        self.failures: dict[str, int] = {}
        self.opened: dict[str, float] = {}
        self.lock = threading.Lock()

    def allow(self, name: str) -> bool:
        with self.lock:
            t = self.opened.get(name)
            if t is None:
                return True
            if time.monotonic() - t > self.cooldown_s:
                self.opened.pop(name, None)
                self.failures[name] = 0
                return True
            return False

    def success(self, name: str) -> None:
        with self.lock:
            self.failures[name] = 0

    def failure(self, name: str) -> None:
        with self.lock:
            self.failures[name] = self.failures.get(name, 0) + 1
            if self.failures[name] >= self.threshold:
                self.opened[name] = time.monotonic()


BREAKER = CircuitBreaker()
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.M)


def _parse(text: str) -> dict:
    return json.loads(_FENCE.sub("", text.strip()))


def cache_key(prompt: Prompt, system: str, user: str) -> str:
    return hashlib.sha256(f"{prompt.id}|{prompt.version}|{system}|{user}".encode()).hexdigest()


class _Replay:
    _data: dict[str, dict] | None = None

    @classmethod
    def get(cls, key: str) -> dict | None:
        if cls._data is None:
            cls._data = {}
            path = get_settings().recordings_path
            if path.exists():
                for line in path.read_text().splitlines():
                    if line.strip():
                        rec = json.loads(line)
                        cls._data[rec["key"]] = rec
        return cls._data.get(key)


class LLMRouter:
    def __init__(self, session: Session, providers: dict[str, object] | None = None):
        self.session = session
        self.settings = get_settings()
        self.providers = configured_providers() if providers is None else providers

    def tokens_used(self, cr_id: int | None) -> int:
        if cr_id is None:
            return 0
        q = select(func.coalesce(func.sum(LLMCall.input_tokens + LLMCall.output_tokens), 0)).where(LLMCall.cr_id == cr_id)
        return int(self.session.execute(q).scalar() or 0)

    def _ledger(self, *, cr_id, node, provider, model, prompt, status, est, in_tok=0, out_tok=0, latency=0,
                cache_hit=False, error="") -> None:
        self.session.add(LLMCall(cr_id=cr_id, node=node, provider=provider, model=model, prompt_id=prompt.id,
                                 prompt_version=prompt.version, input_tokens=in_tok, output_tokens=out_tok,
                                 latency_ms=latency, cache_hit=cache_hit, status=status,
                                 estimated_tokens=est, error=error[:500]))
        self.session.flush()
        metrics.LLM_CALLS.labels(provider, model, node, status).inc()
        metrics.LLM_TOKENS.labels(provider, model, node, "input").inc(in_tok)
        metrics.LLM_TOKENS.labels(provider, model, node, "output").inc(out_tok)

    def _fallback(self, schema: type[M], fallback: Callable[[], dict], reason: str, **ledger) -> LLMResult[M]:
        metrics.LLM_FALLBACKS.labels(ledger["node"], reason.split(":")[0]).inc()
        self._ledger(provider="offline", model="deterministic", status="fallback", error=reason, **ledger)
        return LLMResult(schema.model_validate(fallback()), "offline", "deterministic", False, reason, 0, 0)

    def complete_json(
        self,
        prompt_id: str,
        variables: dict[str, str],
        schema: type[M],
        fallback: Callable[[], dict],
        *,
        node: str,
        cr_id: int | None = None,
    ) -> LLMResult[M]:
        prompt = load_prompt(prompt_id)
        system, user = prompt.render(variables)
        est = estimate_tokens(system + user) + prompt.max_output_tokens
        key = cache_key(prompt, system, user)
        base = {"cr_id": cr_id, "node": node, "prompt": prompt, "est": est}

        with span(f"llm.{prompt_id}", kind="LLM", **{"llm.prompt_template.version": prompt.version,
                                                      "input.value": user[:2000]}) as sp:
            mode = self.settings.llm_mode
            if mode == "offline":
                return self._fallback(schema, fallback, "offline_mode", **base)

            cached = self.session.get(LLMCache, key)
            if cached is not None:
                try:
                    data = schema.model_validate(cached.response)
                    metrics.LLM_CACHE_HITS.labels(node).inc()
                    self._ledger(provider=cached.provider, model=cached.model, status="ok", cache_hit=True, **base)
                    sp.set_attribute("llm.cache_hit", True)
                    return LLMResult(data, cached.provider, cached.model, True, None, 0, 0)
                except ValidationError:
                    pass

            if mode == "replay":
                rec = _Replay.get(key)
                if rec is not None:
                    self._ledger(provider=rec["provider"], model=rec["model"], status="ok", cache_hit=True,
                                 error="replay", **base)
                    return LLMResult(schema.model_validate(rec["response"]), rec["provider"], rec["model"], True, None, 0, 0)
                return self._fallback(schema, fallback, "replay_miss", **base)

            used = self.tokens_used(cr_id)
            if cr_id is not None and used + est > self.settings.token_budget_per_case:
                return self._fallback(schema, fallback, f"budget_exceeded:{used}+{est}", **base)

            errors: list[str] = []
            for name in ROUTES[prompt.model_tier]:
                provider = self.providers.get(name)
                if provider is None:
                    continue
                if not BREAKER.allow(name):
                    errors.append(f"{name}:circuit_open")
                    continue
                result = self._try_provider(provider, prompt, system, user, schema, errors, base)
                if result is not None:
                    data, raw, in_tok, out_tok = result
                    self.session.merge(LLMCache(key=key, provider=name, model=provider.model, response=raw))
                    self.session.flush()
                    if self.settings.llm_record:
                        self._record(key, prompt, name, provider.model, raw)
                    sp.set_attribute("llm.model_name", provider.model)
                    sp.set_attribute("llm.token_count.prompt", in_tok)
                    sp.set_attribute("llm.token_count.completion", out_tok)
                    sp.set_attribute("output.value", json.dumps(raw)[:2000])
                    return LLMResult(data, name, provider.model, False, None, in_tok, out_tok)
            reason = "no_provider_configured" if not errors else "providers_failed:" + "|".join(errors)[:300]
            return self._fallback(schema, fallback, reason, **base)

    def _try_provider(self, provider, prompt: Prompt, system: str, user: str, schema, errors: list[str], base):
        attempt_user = user
        in_total = out_total = 0
        for attempt in range(2):  # 1 call + 1 retry (transient) or repair (invalid JSON)
            t0 = time.monotonic()
            try:
                c = provider.complete(system, attempt_user, prompt.max_output_tokens, prompt.temperature)
            except ProviderError as e:
                latency = int((time.monotonic() - t0) * 1000)
                self._ledger(provider=provider.name, model=provider.model, status="error", latency=latency,
                             error=str(e), **base)
                BREAKER.failure(provider.name)
                errors.append(f"{provider.name}:{str(e)[:80]}")
                if e.transient and attempt == 0:
                    time.sleep(1.0)
                    continue
                return None
            latency = int((time.monotonic() - t0) * 1000)
            in_total += c.input_tokens
            out_total += c.output_tokens
            try:
                raw = _parse(c.text)
                data = schema.model_validate(raw)
            except (json.JSONDecodeError, ValidationError) as e:
                self._ledger(provider=provider.name, model=provider.model, status="invalid_output", latency=latency,
                             in_tok=c.input_tokens, out_tok=c.output_tokens, error=str(e)[:300], **base)
                errors.append(f"{provider.name}:invalid_output")
                attempt_user = (f"{user}\n\nYour previous answer failed validation: {str(e)[:400]}\n"
                                "Return ONLY corrected JSON matching the schema.")
                continue
            BREAKER.success(provider.name)
            self._ledger(provider=provider.name, model=provider.model, status="ok", latency=latency,
                         in_tok=c.input_tokens, out_tok=c.output_tokens, **base)
            return data, raw, in_total, out_total
        BREAKER.failure(provider.name)
        return None

    def _record(self, key: str, prompt: Prompt, provider: str, model: str, raw: dict) -> None:
        path = self.settings.recordings_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write(json.dumps({"key": key, "prompt_id": prompt.id, "version": prompt.version,
                                "provider": provider, "model": model, "response": raw}) + "\n")
