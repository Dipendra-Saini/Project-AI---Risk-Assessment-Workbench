# Stage 1 - Requirements prompts (as used)

Agent: `requirements-analyst` (see `ai/agents/requirements-analyst.md`).
Context given: brief only (about 600 tokens) plus the role prompt. No codebase.

## Prompt R-1: gap analysis
```
Read docs/requirements/00-brief.md. List every decision the brief leaves open
that would change the data model, the workflow, or the scoring. For each,
propose two options with trade-offs. Do not choose. Output a markdown table.
```
Output used to seed `assumptions.md`. Human chose an option per row.

## Prompt R-2: framework research
```
Which published supervisory frameworks (US federal + international standard
setters + industry bodies) define (a) the obligation to risk-assess a new
product before launch, (b) the dimensions of ML/TF/sanctions risk, (c) the
inherent / control / residual methodology, (d) model risk governance?
For each: exact title, issuer, year, one-line summary, public URL. If you are
not certain of a URL or paragraph number, say "unverified" instead of guessing.
```
Output -> `regulatory-research.md` after human verification.

## Prompt R-3: spec expansion
```
Using the brief, the chosen assumptions and the framework list, write a spec
with personas, FR-xx functional requirements and NFR-xx non-functional
requirements. Every requirement must be testable. Add a table that states for
each activity whether it is deterministic, AI, or human, and why.
```

## Prompt R-4: stories
```
Convert each FR into user stories with Given/When/Then acceptance criteria.
Add adversarial stories: LLM outage, prompt injection in an uploaded file,
attempted auto-approval, tampered audit row.
```

## What the human changed
See "Review decisions" at the bottom of `docs/requirements/regulatory-research.md`
and the "Assumption" column of `docs/requirements/assumptions.md`.

## Token use at this stage
4 prompts, brief-only context. Kept small by never attaching the codebase to
requirements prompts.
