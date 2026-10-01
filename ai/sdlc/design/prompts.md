# Stage 2 - Design prompts (as used)

Agent: `architect`. Context: `spec.md`, `assumptions.md`, `AGENTS.md` (about 4k tokens).

## D-1: component split
```
For each activity in spec section 6, propose a component. For every component
that uses an LLM, describe the deterministic alternative, the failure mode of
the LLM version, and how a human would catch that failure. Recommend one.
```
Result: the "Where AI is used" table in `docs/architecture/overview.md`.

## D-2: orchestration options
```
Compare plain functions, CrewAI, AutoGen, Temporal and LangGraph for a pipeline
that must pause for two human approvals, resume after a restart, and loop at most
once between a drafter and a critic. Score each on interrupts, durability,
auditability, operational cost. Free/OSS only.
```
Result: ADR-002.

## D-3: scoring model
```
Propose a scoring model where (a) controls never fully eliminate risk, (b) one
critical dimension cannot be averaged away, (c) all parameters are tunable
config, (d) results are reproducible. Give formulas and the invariants a
property test should check.
```
Result: ADR-001 and `config/v1.yaml`. Human change: the agent proposed additive
control credits; replaced by the multiplicative `1 - prod(1 - e_i)` form so that
stacking many weak controls cannot exceed the cap.

## D-4: data model
```
Design tables so that every AI output keeps its provenance (model, prompt
version, origin), humans' changes are separate override rows, and nothing is
ever overwritten. Output a Mermaid ER diagram.
```
Result: `docs/architecture/data-model.md`.
