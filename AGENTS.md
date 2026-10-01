# AGENTS.md - instructions for every AI coding agent working in this repo

This file is the root of the **build-time harness**. Cursor, Claude Code, Copilot
or any other agent must read it before touching code. Role-specific prompts live
in `ai/agents/`; path-scoped rules live in `.cursor/rules/`.

## Product in one line
Risk Assessment Workbench (RAW): a governed platform that carries a change
request from intake, through financial-crime risk assessment, to a risk
committee decision. **The system prepares, humans decide.**

## Non-negotiable invariants (a PR that breaks one is rejected)
1. **No LLM produces a number that drives a decision.** Scores, tiers and
   workflow transitions come only from `src/backend/raw/scoring` and
   `src/backend/raw/workflow`. LLM output may *suggest* a factor rating; it is
   stored with `origin="ai"` and must be confirmed by a human at gate G1.
2. **Nothing is approved or rejected automatically.** Only
   `workflow.record_decision()` may enter a terminal state, and it requires a
   committee quorum. `tests/unit/test_workflow.py::test_no_auto_decision` guards this.
3. **Controls mitigate, never eliminate.** Residual > 0 and residual <= inherent.
   Property-tested in `tests/unit/test_scoring.py`.
4. **The audit log is append-only and hash-chained.** Never write an UPDATE or
   DELETE against `audit_events`. Use `audit.record()`.
5. **Synthetic data only.** Never add real customer, bank or person data.
6. **Every AI claim is cited.** Drafted narrative sentences reference
   `[chunk:<id>]` ids that exist in `policy_chunks`.

## Where things live
| Path | Purpose |
|---|---|
| `src/backend/raw/` | FastAPI app, domain, graph, scoring, workflow, audit, rag, llm |
| `src/frontend/` | React + Vite UI |
| `ai/prompts/` | Versioned runtime prompts (YAML). Change => bump `version` |
| `ai/agents/` | Build-time subagent role prompts |
| `ai/failure-log.md` | Every agent failure, how it was detected, what changed |
| `config/` | Analyst-tunable scoring + workflow config |
| `evals/` | Golden datasets, eval runner, results history |
| `docs/` | Requirements, architecture (ADRs), governance |

## Working agreement for agents
- Plan -> small change -> run `make test` -> commit. One concern per commit.
- When a requirement is ambiguous, write the assumption in
  `docs/requirements/assumptions.md` instead of guessing silently.
- When you fail (stall, hallucinated API, broken test loop > 2 tries), stop and
  append an entry to `ai/failure-log.md` before continuing.
- Prompts: never inline a prompt string in Python. Load from `ai/prompts/` via
  `raw.llm.prompts.load_prompt()` so version + token caps are tracked.
- Prefer deterministic code over an LLM call whenever the problem has a
  checkable right answer (see `docs/architecture/adr/ADR-001`).
- Keep token cost visible: every LLM call goes through `raw.llm.router.LLMRouter`,
  which writes to the `llm_calls` ledger.

## Commands
```
make setup      # venv + deps + frontend deps
make seed       # synthetic data + policy ingestion
make api        # backend on :8000
make web        # frontend on :5173
make test       # unit + api tests
make evals      # eval suite (LLM_MODE=replay by default, zero tokens)
make tokens     # regenerate ops/token-analysis.md
```
