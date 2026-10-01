# Runbook

Who: the platform engineer on call, with the FCRM analyst lead for anything that changes a risk outcome.
Where to look: Grafana "Risk Assessment Workbench" (:3000), Prometheus alerts (:9090/alerts),
Phoenix traces (:6006, one trace per graph node and per LLM call), API logs (`docker compose logs api`).

The safety property that matters most: **no case can reach a decision without people**. Every failure
mode below degrades to "slower and less AI help". None of them degrades to "wrong decision recorded".
If you see anything that contradicts that, treat it as a P1 and stop the service.

---

## ApiDown
**Symptom** Prometheus can't scrape `/metrics`; the UI shows network errors.
1. `docker compose -f ops/deploy/docker-compose.yml ps`: is `api` running and healthy?
2. `docker compose logs --tail 200 api`. Common causes: the database isn't reachable (check `db` health),
   a failed migration (the `alembic upgrade head` error is at the top of the log), or a bad `JWT_SECRET` / env.
3. Restart: `docker compose up -d api`. In-flight graph runs resume from the Postgres checkpoint on the next action;
   a case showing `pipeline_state = running` with no progress after 5 minutes can be re-run by an analyst
   ("Re-run full assessment") or the PO ("Re-run extraction").

## PipelineNodeErrors
**Symptom** One graph node fails repeatedly. The case gets `pipeline_state = failed` and a warning, and stays in its state.
1. Phoenix: filter traces by `node.<name>` and read the exception on the failing span.
2. Ledger: `select node, status, error from llm_calls order by id desc limit 20;`.
3. Data issue (e.g. an unparseable upload): ask the PO to re-upload. Code issue: roll back the API image tag.
4. Never edit case rows by hand. The audit chain will flag it, and the database blocks changes to `audit_events`.

## LlmFallbackRateHigh
**Symptom** More than half of LLM requests are answered by the deterministic fallback. Cases still flow:
extraction is keyword-based and drafts quote policy text, so analysts do more by hand.
1. Grafana "Fallbacks" panel, split by `reason`:
   - `providers_failed:...429`: free-tier rate limit. Lower load or wait for the quota window. To stretch the quota:
     lower `TOKEN_BUDGET_PER_CASE`, shorten passages (`_passages(limit=...)` in `graph/nodes.py`).
   - `circuit_open`: the breaker opened after 3 failures in a row and retries after 60 s. No action unless it persists.
   - `budget_exceeded`: a case hit the per-case token budget. Usually very long uploads. Raise the budget only with a reason.
   - `no_provider_configured`: `GEMINI_API_KEY` / `GROQ_API_KEY` are missing in the API environment.
2. Provider status pages: Google AI Studio, Groq console.
3. A fallback never blocks a gate. AI-suggested factors from the fallback are still marked for analyst confirmation (G1).

## CriticUnsupportedSpike
**Symptom** The narrative critic flags many sentences. That's a groundedness regression: the drafter is claiming things its
cited passages don't support.
1. Phoenix: open recent `llm.draft_assessment` spans. Compare the output with the `llm.critique_claims` verdicts.
2. Did a prompt or model change ship? Check `ai/prompts/draft_assessment.yaml` history and the `model` column in `llm_calls`.
   Free-tier providers sometimes change a model behind the same name.
3. Run `make evals` in live mode against the golden set. If groundedness < 0.90, pin the previous prompt
   version or switch the large tier to the other provider (`ROUTES` in `llm/providers.py`).
4. Analysts can't sign a narrative with unresolved warnings without writing a reason (G2), so this is a quality
   problem, not a control failure.

## AiSuggestionOverrideRateHigh
**Symptom** Analysts override more than 40% of AI factor suggestions in a week. That's model drift, or a new kind of product the
prompts don't cover.
1. `PYTHONPATH=src/backend .venv/bin/python scripts/overrides_to_evals.py` exports the corrected cases.
2. FCRM SME reviews them and moves good ones into a new golden set version (`evals/datasets/golden_v2.yaml`).
3. Improve the prompt or add a rule (`config/v1.yaml` through the Config page). Run evals and compare with the last run in `evals/results/`.

## DecisionReadySlaBreached
**Symptom** p90 time from submission to committee-ready is over 2 days (the brief's success metric).
1. Case list → "Needs analyst review": a queue backlog is a staffing issue, not a system one.
2. Many cases in `INFO_REQUESTED`? Look for a pattern in the analyst requests; it may point to an intake form gap.
3. Pipeline time itself is seconds (`raw_pipeline_node_seconds`). If it isn't, see LlmFallbackRateHigh.

---

## Routine operations

| task | how |
|---|---|
| Change scoring weights, tiers, quorum | Config page (analyst). Every save is a new immutable version with a note. Existing assessments keep their version. Run `evals/run_evals.py --config <candidate>` first. |
| Rotate `JWT_SECRET` | Set the new value and restart the API. All sessions log out. |
| Verify audit integrity | Audit page → "Verify chain integrity", or `GET /api/audit/verify`. Schedule it daily. |
| Examiner request | Case → "Examiner pack" (HTML) or `GET /api/cases/{id}/examiner-pack` (JSON): facts, scores with config hash, citations, overrides, votes, decision, chain proof. |
| Back up | `pg_dump` of the `raw` database. `audit_events`, `llm_calls` and `config_versions` are the regulatory record. |
| Re-ingest policies after an edit | Restart the API. `ensure_reference_data` re-ingests changed chunks idempotently, keyed by chunk id and text hash. |
| Record fresh LLM replays for CI | `make evals-live` with free keys set, then commit `evals/recordings/llm_recordings.jsonl`. |
