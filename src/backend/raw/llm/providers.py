"""Free-tier LLM providers over plain HTTP (no SDK lock-in)."""

from dataclasses import dataclass

import httpx

from raw.settings import get_settings


class ProviderError(Exception):
    def __init__(self, msg: str, transient: bool):
        super().__init__(msg)
        self.transient = transient


@dataclass
class Completion:
    text: str
    input_tokens: int
    output_tokens: int


def _raise_for(r: httpx.Response, name: str) -> None:
    if r.status_code >= 400:
        transient = r.status_code == 429 or r.status_code >= 500
        raise ProviderError(f"{name} HTTP {r.status_code}: {r.text[:200]}", transient)


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str):
        self.api_key, self.model = api_key, model

    def complete(self, system: str, user: str, max_tokens: int, temperature: float) -> Completion:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
                # Structured drafting does not need reasoning tokens; they would eat the output cap.
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }
        try:
            r = httpx.post(url, params={"key": self.api_key}, json=body, timeout=get_settings().llm_timeout_s)
        except httpx.TransportError as e:
            raise ProviderError(f"gemini transport: {e}", True) from e
        _raise_for(r, "gemini")
        data = r.json()
        try:
            text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
        except (KeyError, IndexError) as e:
            raise ProviderError(f"gemini empty response: {str(data)[:200]}", True) from e
        usage = data.get("usageMetadata", {})
        return Completion(text, usage.get("promptTokenCount", 0), usage.get("candidatesTokenCount", 0))


class GroqProvider:
    name = "groq"

    def __init__(self, api_key: str, model: str):
        self.api_key, self.model = api_key, model

    def complete(self, system: str, user: str, max_tokens: int, temperature: float) -> Completion:
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        try:
            r = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=body,
                timeout=get_settings().llm_timeout_s,
            )
        except httpx.TransportError as e:
            raise ProviderError(f"groq transport: {e}", True) from e
        _raise_for(r, "groq")
        data = r.json()
        usage = data.get("usage", {})
        return Completion(data["choices"][0]["message"]["content"], usage.get("prompt_tokens", 0),
                          usage.get("completion_tokens", 0))


def configured_providers() -> dict[str, object]:
    s = get_settings()
    out: dict[str, object] = {}
    if s.gemini_api_key:
        out["gemini"] = GeminiProvider(s.gemini_api_key, s.gemini_model)
    if s.groq_api_key:
        out["groq"] = GroqProvider(s.groq_api_key, s.groq_model)
    return out


ROUTES = {"small": ["groq", "gemini"], "large": ["gemini", "groq"]}
