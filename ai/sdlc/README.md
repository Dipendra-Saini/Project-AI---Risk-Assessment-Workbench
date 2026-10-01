# AI across the six delivery stages

This folder stores the prompts used at each SDLC stage and what the human
changed in the AI output. Runtime prompts (used by the product) are in
`ai/prompts/`; build-time role prompts are in `ai/agents/`.

| Stage | AI did | Human did | Evidence |
|---|---|---|---|
| 1 Requirements | Expanded the brief into spec, stories, assumptions; researched frameworks | Removed invented dimension, unverifiable paragraph refs; set quorum/tie rule | `requirements/`, `docs/requirements/` |
| 2 Design | Proposed architecture, ERD, ADR options with trade-offs | Chose deterministic scoring and LangGraph; set gate placement | `design/`, `docs/architecture/` |
| 3 Development | Implemented modules role by role under `AGENTS.md` rules | Reviewed diffs against the reviewer checklist | commit history, `.cursor/rules/` |
| 4 Testing | Generated tests from user stories, adversarial cases, golden eval set | Promoted eval cases, set thresholds | `tests/`, `evals/` |
| 5 Deployment | Wrote Dockerfiles, compose, CI | Chose free hosting path, go-live checklist sign-off | `ops/deploy/`, `.github/` |
| 6 Operations | Generated dashboards, alerts, token report; drafts eval cases from overrides | Triage alerts, approve config changes | `ops/monitoring/`, `scripts/overrides_to_evals.py` |
