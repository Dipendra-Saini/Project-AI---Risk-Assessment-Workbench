# Eval run 2026-10-01 21:06 UTC - candidate-a-floor07

Mode **offline** | scoring config `config/candidate-a-floor07.yaml` (hash `c0ecf31998bb`) | dataset `golden_v1.yaml` (25 cases) | prompts extract_intake@1.0, classify_change@1.0, suggest_factor@1.0, draft_assessment@1.0, critique_claims@1.0

## Gates

| metric | value | threshold | result |
|---|---|---|---|
| extraction_list_f1 | 0.982 | >= 0.85 | PASS |
| extraction_flag_accuracy | 0.992 | >= 0.9 | PASS |
| retrieval_must_cite_recall | 0.793 | >= 0.6 | PASS |
| tier_within_one | 1.0 | >= 0.95 | PASS |
| tier_under_rate | 0.32 | <= 0.1 | FAIL |
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
| tier_exact | 0.6 |
| tier_within_one | 1.0 |
| tier_over | 2 |
| tier_under | 8 |
| tier_under_rate | 0.32 |
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
| p95_seconds | 0.03 |

## Residual tier confusion (designer label vs system)

| expected \ got | Low | Medium | High | Critical |
|---|---|---|---|---|
| **Low** | 0 | 2 | 0 | 0 |
| **Medium** | 1 | 13 | 0 | 0 |
| **High** | 0 | 6 | 2 | 0 |
| **Critical** | 0 | 0 | 1 | 0 |

## Per case

| case | tier exp | tier got | residual | list F1 | ctl F1 | must-cite recall | claims ok | tokens | notes |
|---|---|---|---|---|---|---|---|---|---|
| G01 | Medium | Medium | 8.4 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| G02 | High | High | 14.0 | 1.00 | 0.80 | 0.67 | 19/19 | 0 |  |
| G03 | Low | Medium * | 6.3 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| G04 | High | Medium * | 11.2 | 1.00 | 1.00 | 0.67 | 19/19 | 0 |  |
| G05 | Medium | Medium | 11.2 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| G06 | Medium | Medium | 7.91 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| G07 | Medium | Medium | 11.2 | 0.93 | 1.00 | 1.00 | 19/19 | 0 |  |
| G08 | Medium | Medium | 11.07 | 1.00 | 1.00 | 0.50 | 19/19 | 0 |  |
| G09 | High | Medium * | 8.4 | 0.91 | 1.00 | 1.00 | 19/19 | 0 |  |
| G10 | Medium | Medium | 8.4 | 1.00 | 1.00 | 0.50 | 19/19 | 0 |  |
| G11 | High | Medium * | 11.2 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| G12 | Medium | Medium | 8.4 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| G13 | Critical | High * | 17.5 | 0.91 | 1.00 | 1.00 | 19/19 | 0 |  |
| G14 | Medium | Low * | 5.56 | 1.00 | 1.00 | 0.50 | 19/19 | 0 |  |
| G15 | Medium | Medium | 7.08 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| G16 | High | Medium * | 10.64 | 0.91 | 1.00 | 1.00 | 19/19 | 0 |  |
| G17 | High | Medium * | 11.2 | 1.00 | 1.00 | 1.00 | 19/19 | 0 | injection flagged |
| G18 | Medium | Medium | 6.8 | 1.00 | 1.00 | 0.00 | 19/19 | 0 | 4 factors pending human |
| G19 | Medium | Medium | 11.2 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| G20 | Medium | Medium | 8.4 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| G21 | Medium | Medium | 11.2 | 1.00 | 1.00 | 0.50 | 19/19 | 0 |  |
| G22 | High | High | 17.5 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| G23 | Medium | Medium | 11.2 | 1.00 | 1.00 | 0.50 | 19/19 | 0 |  |
| G24 | High | Medium * | 8.4 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| G25 | Low | Medium * | 6.3 | 1.00 | 1.00 | 0.00 | 19/19 | 0 |  |

`*` = tier disagrees with the designer label. Labels are judgement calls pending SME review; a disagreement is a prompt for analyst review, not automatically a system error.
