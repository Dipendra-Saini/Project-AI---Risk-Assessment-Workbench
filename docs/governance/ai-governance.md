# AI governance (NIST AI RMF and SR 11-7 aligned)

| Function | What we do | Where |
|---|---|---|
| **Govern** | Invariants in `AGENTS.md`; AI never decides (ADR-006); every model/prompt version recorded on its outputs; change control for prompts (version bump + eval run) | `AGENTS.md`, `.cursor/rules/prompts-and-evals.mdc` |
| **Map** | Inventory of AI components, purpose, tier, deterministic alternative | `docs/architecture/overview.md` table |
| **Measure** | Eval suite: extraction F1, retrieval recall@5/MRR, tier agreement, groundedness, consistency, cost | `evals/` |
| **Manage** | Human gates G0-G3, override feedback loop, budget and circuit breaker, drift alerts on override rate | `docs/governance/review-gates.md`, `ops/monitoring/` |

## Model inventory
| Id | Purpose | Provider (free) | Prompt | Validation |
|---|---|---|---|---|
| M-01 | Intake extraction | Groq qwen/qwen3.8-27b -> Gemini Flash | `ai/prompts/extract_intake.yaml` | Schema + span check + G0 |
| M-02 | Change-type fallback classifier | Groq | `classify_change.yaml` | Enum schema |
| M-03 | Factor suggestion (rule gaps) | Groq | `suggest_factor.yaml` | Schema, range 1-5, citation must exist, G1 |
| M-04 | Narrative drafter | Gemini Flash -> Groq | `draft_assessment.yaml` | Citation check, critic, G2 |
| M-05 | Grounding critic | Gemini Flash | `critique_claims.yaml` | Only on ambiguous sentences |
| M-06 | Embeddings | Gemini embedding | - | Retrieval evals |
| D-01 | Scoring engine (deterministic model) | code | - | Property + regression tests |

## Prompt-injection and untrusted input
Uploaded documents are wrapped in `<document>` delimiters with an explicit
instruction that their contents are data. A deterministic screen flags
instruction-like text; flagged cases show a warning at G0 and G1. Extraction
spans are verified against the source text, so an injected "fact" without a
real span is downgraded.

## Monitoring for drift
- Override rate per dimension (alert if > 40% over 20 cases: rules or prompts are off).
- Offline-fallback rate (alert if > 20%: provider or quota problem).
- Critic unsupported-sentence rate.
