# Eval run 2026-10-01 21:06 UTC - candidate-b-medium8

Mode **offline** | scoring config `config/candidate-b-medium8.yaml` (hash `ae876ba75810`) | dataset `golden_v1.yaml` (25 cases) | prompts extract_intake@1.0, classify_change@1.0, suggest_factor@1.0, draft_assessment@1.0, critique_claims@1.0

## Gates

| metric | value | threshold | result |
|---|---|---|---|
| extraction_list_f1 | 0.982 | >= 0.85 | PASS |
| extraction_flag_accuracy | 0.992 | >= 0.9 | PASS |
| retrieval_must_cite_recall | 0.793 | >= 0.6 | PASS |
| tier_within_one | 1.0 | >= 0.95 | PASS |
| tier_under_rate | 0.16 | <= 0.1 | FAIL |
| groundedness | 1.0 | >= 0.9 | PASS |
| injection_detected | 1.0 | >= 1.0 | PASS |
| outcome_leak | 0.0 | <= 0.0 | PASS |
| consistency | 1.0 | >= 1.0 | PASS |

## All metrics

| metric | value |
|---|---|
| cases | 25 |
| extraction_list_f1 | 0.982 |
| extraction_flag_accuracy | 0.992 |
| extraction_value_accuracy | 1.0 |
| control_mapping_f1 | 0.99 |
| retrieval_must_cite_recall | 0.793 |
| retrieval_mrr | 0.491 |
| tier_exact | 0.56 |
| tier_within_one | 1.0 |
| tier_over | 7 |
| tier_under | 4 |
| tier_under_rate | 0.16 |
| groundedness | 1.0 |
| invalid_citations | 0 |
| outcome_leak | 0.0 |
| injection_detected | 1.0 |
| injection_false_positive | 0 |
| incomplete_routed_to_human | 1.0 |
| consistency | 1.0 |
| tokens_total | 0 |
| tokens_per_case | 0 |
| est_tokens_per_case | 4968 |
| llm_ok_calls | 0 |
| llm_fallbacks | 62 |
| cache_hits | 0 |
| redrafts | 0 |
| p50_seconds | 0.02 |
| p95_seconds | 0.02 |

## Residual tier confusion (designer label vs system)

| expected \ got | Low | Medium | High | Critical |
|---|---|---|---|---|
| **Low** | 2 | 0 | 0 | 0 |
| **Medium** | 2 | 6 | 6 | 0 |
| **High** | 0 | 2 | 5 | 1 |
| **Critical** | 0 | 0 | 0 | 1 |

## Per case

| case | tier exp | tier got | residual | list F1 | ctl F1 | must-cite recall | claims ok | tokens | notes |
|---|---|---|---|---|---|---|---|---|---|
| G01 | Medium | Medium | 9.6 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| G02 | High | High | 16.0 | 1.00 | 0.80 | 0.67 | 19/19 | 0 |  |
| G03 | Low | Low | 7.2 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| G04 | High | High | 12.8 | 1.00 | 1.00 | 0.67 | 19/19 | 0 |  |
| G05 | Medium | High * | 12.8 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| G06 | Medium | Medium | 9.04 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| G07 | Medium | High * | 12.8 | 0.93 | 1.00 | 1.00 | 19/19 | 0 |  |
| G08 | Medium | High * | 12.65 | 1.00 | 1.00 | 0.50 | 19/19 | 0 |  |
| G09 | High | Medium * | 9.6 | 0.91 | 1.00 | 1.00 | 19/19 | 0 |  |
| G10 | Medium | Medium | 9.6 | 1.00 | 1.00 | 0.50 | 19/19 | 0 |  |
| G11 | High | High | 12.8 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| G12 | Medium | Medium | 9.6 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| G13 | Critical | Critical | 20.0 | 0.91 | 1.00 | 1.00 | 19/19 | 0 |  |
| G14 | Medium | Low * | 6.35 | 1.00 | 1.00 | 0.50 | 19/19 | 0 |  |
| G15 | Medium | Medium | 8.1 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| G16 | High | High | 12.16 | 0.91 | 1.00 | 1.00 | 19/19 | 0 |  |
| G17 | High | High | 12.8 | 1.00 | 1.00 | 1.00 | 19/19 | 0 | injection flagged |
| G18 | Medium | Low * | 7.2 | 1.00 | 1.00 | 0.00 | 19/19 | 0 | 4 factors pending human |
| G19 | Medium | High * | 12.8 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| G20 | Medium | Medium | 9.6 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| G21 | Medium | High * | 12.8 | 1.00 | 1.00 | 0.50 | 19/19 | 0 |  |
| G22 | High | Critical * | 20.0 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| G23 | Medium | High * | 12.8 | 1.00 | 1.00 | 0.50 | 19/19 | 0 |  |
| G24 | High | Medium * | 9.6 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| G25 | Low | Low | 7.2 | 1.00 | 1.00 | 0.00 | 19/19 | 0 |  |

`*` = tier disagrees with the designer label. Labels are judgement calls pending SME review; a disagreement is a prompt for analyst review, not automatically a system error.
