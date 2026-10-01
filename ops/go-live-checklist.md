# Go-live checklist

Status key: [x] done in this repo, [ ] needs the bank's environment or people.

## Controls and governance
- [x] No code path lets AI or automation record a decision: static test `test_no_auto_decision_static_guard`, plus `record_decision` is the only writer of terminal states
- [x] Human gates G0, G1, G1b, G2, G3 enforced server-side (`services/gates.py`) and covered by API and E2E tests
- [x] Every override needs a reason; tier-changing overrides need a second analyst
- [x] Audit trail is append-only (DB triggers on SQLite and Postgres) and hash-chained; verification endpoint and UI
- [x] Scoring config is versioned and immutable; each assessment records the config version and hash it used
- [x] Model inventory and AI risk assessment (`docs/governance/ai-governance.md`, SR 11-7 / NIST AI RMF mapping)
- [ ] Model risk management review of the LLM components (M-01..M-06) by the bank's MRM function
- [ ] FCRM SME sign-off on the golden-set tier labels (currently designer judgement, see `evals/README.md`)
- [ ] Policy corpus replaced with the bank's actual policies (current corpus is synthetic and fictional)

## Security
- [x] RBAC on every endpoint; product owners only see their own cases (API tests)
- [x] Prompt-injection screen on submissions; extracted values checked against source spans
- [x] Upload limits (5 MB) and type parsing (PDF / DOCX / TXT / MD only)
- [x] No secrets in the repo; `.env` ignored; compose reads keys from the environment
- [ ] SSO (OIDC / SAML) in place of demo passwords; `JWT_SECRET` from a secrets manager
- [ ] Data classification sign-off for sending product documents to external LLM APIs. Free-tier terms may allow providers to
      use inputs for training, so production needs paid / enterprise terms or a self-hosted model behind the same router.
      This is the one place the free-only constraint of the hackathon doesn't carry into production.
- [ ] Penetration test

## Reliability and operations
- [x] Health check, Prometheus metrics, 6 alert rules each linked to a runbook section
- [x] OpenTelemetry traces with OpenInference attributes (Phoenix)
- [x] Graceful degradation: circuit breaker, retry, deterministic fallback, per-case token budget
- [x] Load smoke: 0% errors, read p95 65 ms at 20 concurrent users (`tests/load/results.md`)
- [x] Postgres + pgvector production path verified (compose stack and CI job)
- [ ] Backups and restore drill for the `raw` database
- [ ] Alert routing (PagerDuty / Teams) configured

## Quality
- [x] Unit, property-based (hypothesis), API and E2E tests in CI
- [x] Eval gates in CI on replayed LLM responses, including the under-rating gate
- [ ] Live-mode eval baseline recorded with the production model versions (`make evals-live`)
- [ ] Parallel run: 4-6 weeks assessing real changes in both the old process and the workbench, then comparing outcomes and time to decision-ready
