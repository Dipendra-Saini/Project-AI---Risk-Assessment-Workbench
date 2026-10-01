# Load smoke results

Run: 2026-10-01, `grafana/k6` in Docker against a single uvicorn worker on a MacBook. SQLite, `LLM_MODE=offline`.
Scenario (`smoke.js`): 20 virtual users reading the case list and case detail continuously for 60 s, plus
0.5 intake/s (create a case and start the AI pipeline).

| threshold | result | limit | |
|---|---|---|---|
| request failure rate | 0.00% (0 / 2,388) | < 1% | pass |
| read p95 | 65 ms | < 500 ms | pass |
| write p95 | 36 ms | < 2,000 ms | pass |
| checks | 100% | > 99% | pass |

All 31 pipelines started under load completed and parked at the product-owner gate (G0), with no
server errors. Throughput was about 39 requests/s; the latency profile was flat (p99 103 ms, max 134 ms).

## What this does and doesn't show
- The API, ORM, audit chain and background pipeline dispatch hold up under a realistic team-sized load
  (a financial-crime risk function is tens of users, not thousands).
- `POST /extract` returns as soon as the pipeline is queued, so write latency excludes pipeline time. Pipeline
  time is measured separately: offline about 20 ms per case (`evals/results`). Live free-tier LLMs take 3-10 s per
  case and are bounded by provider rate limits (Groq / Gemini free tiers), not by this service. The router's
  circuit breaker and deterministic fallback keep cases moving when those limits are hit (`tests/unit/test_llm_router.py`).
- SQLite serialises writes. Production runs on Postgres (`ops/deploy/docker-compose.yml`), and CI runs the
  lifecycle against Postgres + pgvector.
