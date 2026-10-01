# ADR-004: Free-tier model routing, caching and budgets

Status: Accepted

## Context
Constraint: free tools only. Free tiers have rate limits and occasional
outages. Token efficiency is judged.

## Decision
- Two tiers: `small` (extraction, classification, factor suggestions) routes to
  Groq `llama-3.1-8b-instant` first, Gemini Flash second. `large` (drafting,
  critique) routes to Gemini Flash first, Groq second.
- JSON mode on both providers + Pydantic validation + one repair retry.
- Gemini "thinking" budget set to 0: structured drafting does not need it and
  thinking tokens count against output limits.
- Response cache keyed by `sha256(prompt_id, prompt_version, model, rendered input)`.
- Per-case token budget (default 12k); when exceeded, the router returns the
  deterministic fallback and records a warning instead of calling the model.
- Circuit breaker per provider: 3 consecutive failures => 60 s open.
- Modes: `live`, `offline` (deterministic providers only), `replay` (recorded
  responses, then offline). CI and evals default to `replay` = zero tokens.

## Consequences
The demo cannot fail for lack of a key or quota. Accepted risk: the offline
provider is weaker; its use is always flagged on the case so humans know.
