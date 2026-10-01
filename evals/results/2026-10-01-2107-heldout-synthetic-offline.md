# Eval run 2026-10-01 21:07 UTC - heldout-synthetic-offline

Mode **offline** | scoring config `config/v1.yaml` (hash `a3ec3b1d2b63`) | dataset `change_requests.jsonl` (40 cases) | prompts extract_intake@1.0, classify_change@1.0, suggest_factor@1.0, draft_assessment@1.0, critique_claims@1.0

## Gates

| metric | value | threshold | result |
|---|---|---|---|
| extraction_list_f1 | 1.0 | >= 0.85 | PASS |
| extraction_flag_accuracy | 1.0 | >= 0.9 | PASS |
| retrieval_must_cite_recall | 1.0 | >= 0.6 | PASS |
| groundedness | 1.0 | >= 0.9 | PASS |
| injection_detected | 1.0 | >= 1.0 | PASS |
| outcome_leak | 0.0 | <= 0.0 | PASS |
| consistency | 1.0 | >= 1.0 | PASS |

## All metrics

| metric | value |
|---|---|
| cases | 40 |
| extraction_list_f1 | 1.0 |
| extraction_flag_accuracy | 1.0 |
| extraction_value_accuracy | 1.0 |
| control_mapping_f1 | 1.0 |
| retrieval_must_cite_recall | 1.0 |
| retrieval_mrr | 1.0 |
| tier_labelled_cases | 0 |
| tier_exact | 0.0 |
| tier_within_one | 0.0 |
| tier_over | 0 |
| tier_under | 0 |
| tier_under_rate | 0.0 |
| groundedness | 1.0 |
| invalid_citations | 0 |
| outcome_leak | 0.0 |
| injection_detected | 1.0 |
| injection_false_positive | 0 |
| incomplete_routed_to_human | 1.0 |
| consistency | 1.0 |
| tokens_total | 0 |
| tokens_per_case | 0 |
| est_tokens_per_case | 4729 |
| llm_ok_calls | 0 |
| llm_fallbacks | 88 |
| cache_hits | 0 |
| redrafts | 0 |
| p50_seconds | 0.02 |
| p95_seconds | 0.03 |

## Residual tier confusion (designer label vs system)

| expected \ got | Low | Medium | High | Critical |
|---|---|---|---|---|
| **Low** | 0 | 0 | 0 | 0 |
| **Medium** | 0 | 0 | 0 | 0 |
| **High** | 0 | 0 | 0 | 0 |
| **Critical** | 0 | 0 | 0 | 0 |

## Per case

| case | tier exp | tier got | residual | list F1 | ctl F1 | must-cite recall | claims ok | tokens | notes |
|---|---|---|---|---|---|---|---|---|---|
| S001 | None | Critical | 20.0 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S002 | None | Medium | 6.35 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S003 | None | Medium | 11.6 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S004 | None | High | 16.0 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S005 | None | High | 16.0 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S006 | None | High | 12.8 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S007 | None | High | 16.0 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S008 | None | Medium | 9.6 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S009 | None | High | 12.8 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S010 | None | High | 12.8 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S011 | None | Critical | 20.0 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S012 | None | High | 12.8 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S013 | None | High | 12.8 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S014 | None | Critical | 20.0 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S015 | None | High | 16.0 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S016 | None | High | 13.97 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S017 | None | High | 12.8 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S018 | None | High | 12.8 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S019 | None | High | 12.8 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S020 | None | Critical | 20.0 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S021 | None | Medium | 9.6 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S022 | None | Medium | 9.6 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S023 | None | Critical | 20.0 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S024 | None | High | 12.8 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S025 | None | Critical | 20.0 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S026 | None | High | 12.8 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S027 | None | Medium | 9.6 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S028 | None | High | 12.8 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S029 | None | High | 12.65 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S030 | None | High | 12.8 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S031 | None | High | 16.0 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S032 | None | High | 12.8 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S033 | None | Critical | 20.0 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S034 | None | High | 12.8 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S035 | None | Medium | 6.7 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S036 | None | Medium | 7.2 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S037 | None | Medium | 7.43 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S038 | None | Medium | 8.38 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S039 | None | High | 12.8 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |
| S040 | None | High | 12.65 | 1.00 | 1.00 | 1.00 | 19/19 | 0 |  |

`*` = tier disagrees with the designer label. Labels are judgement calls pending SME review; a disagreement is a prompt for analyst review, not automatically a system error.
