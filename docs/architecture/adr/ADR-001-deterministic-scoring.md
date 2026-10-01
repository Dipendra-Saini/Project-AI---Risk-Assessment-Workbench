# ADR-001: Risk scoring is deterministic; LLMs never produce a score

Status: Accepted

## Context
The brief's core pains are inconsistency ("two analysts reach different
conclusions") and untraceable ratings. Scoring parameters must be tunable by
the risk function, and the output must be explainable to an examiner. SR 11-7
treats a scoring method as a model that must be documented and validated.

## Options considered
1. **LLM rates and scores each dimension.** Fast to build; non-reproducible,
   hard to tune, untestable invariants, and an examiner cannot replay it.
2. **LLM rates factors, code scores.** Better, but factor ratings still vary run
   to run.
3. **Rule engine rates factors where a rule matches, LLM suggests only for gaps
   (flagged, human-confirmed), code scores.** Chosen.

## Decision
- Inherent per dimension = likelihood (1-5) x impact (1-5).
- Overall = max(weighted mean, `max_dimension_floor_ratio` x worst dimension).
- Control effectiveness e = design x operating; combined per dimension as
  `1 - prod(1 - e_i)`; mitigation = combined x `mitigation_cap` (cap < 1).
- Residual = max(inherent x (1 - mitigation), `residual_floor_ratio` x inherent).
- Tier thresholds, weights, cap and floors live in versioned config.
- Every result carries a trace: inputs, rule ids, formula steps, config hash.

## Consequences
- Same inputs + same config version => identical score, forever.
- "Controls never eliminate risk" is a property test, not a hope.
- Rules need curation by FCRM; AI suggestions cover the long tail meanwhile, and
  every accepted AI suggestion is a candidate for a new rule.
- Accepted risk: rules can be coarse. Mitigated by analyst override with reason.
