# Evals

The pipeline is evaluated end to end. Each golden case goes through the same graph, services and
scoring code as the API, on a throwaway SQLite database. A failing gate fails CI.

```bash
make evals                                                   # replay mode: recorded LLM responses, $0, deterministic
.venv/bin/python evals/run_evals.py --mode offline           # no LLM at all (deterministic fallbacks)
.venv/bin/python evals/run_evals.py --mode live --record     # free-tier Gemini/Groq; writes evals/recordings/ for replay
.venv/bin/python evals/run_evals.py --config config/candidate-a-floor07.yaml --label cand-a   # evaluate a config change
.venv/bin/python evals/run_evals.py --dataset data/synthetic/change_requests.jsonl --label heldout   # held-out extraction set
```

Each run writes `results/<timestamp>-<label>.md` (human-readable) and `.json` (machine-readable).
Results are committed so the history of iterations is visible in git.

## Datasets

| file | cases | labels | purpose |
|---|---|---|---|
| `datasets/golden_v1.yaml` | 25 hand-written (G01-G25) | facts, controls, residual tier, must-cite policy chunks, injection / incomplete flags | main regression set |
| `data/synthetic/change_requests.jsonl` | 40 generated (S001-S040) | facts only | held-out extraction check (never used while tuning) |
| `datasets/candidates_from_overrides.yaml` | grows with use | human-corrected facts and tiers | feedback loop: `scripts/overrides_to_evals.py` turns every analyst or PO override into a *candidate* case for SME review |

The tier labels in `golden_v1` were written by the scenario designer **before** the scoring engine ran,
so the comparison isn't circular. They're still judgement calls, marked *pending FCRM SME review*. A
disagreement means "an analyst should look at this", not automatically "the system is wrong". Dataset
versions are immutable: corrections go into `golden_v2.yaml`.

## Metrics and gates

| metric | what it catches | gate |
|---|---|---|
| `extraction_list_f1` | wrong or missed customer types, geographies, channels, third-party roles | >= 0.85 |
| `extraction_flag_accuracy` | cross-border / cash / crypto / instant / anonymous flags | >= 0.90 |
| `control_mapping_f1` | proposed controls mapped to the wrong library control | reported |
| `retrieval_must_cite_recall` | policy sections the assessment must rely on but the drafter never sees | >= 0.60 |
| `retrieval_mrr` | how high the right section ranks | reported |
| `tier_within_one` | gross scoring errors | >= 0.95 |
| `tier_under_rate` | **under-rating risk**: the costly error for a financial-crime function | <= 0.10 |
| `tier_exact` | calibration against designer labels | reported |
| `groundedness` | narrative claims the critic could not verify against cited text | >= 0.90 |
| `outcome_leak` | narrative recommending approve or reject (ADR-006) | = 0 |
| `injection_detected` | prompt injection in submitted documents gets flagged | = 1.0 |
| `incomplete_routed_to_human` | thin submissions produce pending factors, not confident scores | reported |
| `consistency` | same input run twice gives the same tier and factor table | = 1.0 |
| tokens, LLM calls, fallbacks, cache hits, p50 / p95 latency | cost and degradation | reported, tracked in `ops/token-analysis.md` |

Gates only ever move up. Lowering one needs an entry in this file explaining why.

## Iteration history

Runs 1-4 are offline mode. That measures the deterministic part of the system: rules, scoring,
retrieval, the critic's deterministic checks, the safety screens and the fallback extractor the
system degrades to when every free-tier provider is down. Live and replay runs use the same harness
once free-tier keys are configured (`--mode live --record`). They are what measure the LLM extractor
and drafter.

### Run 1 - baseline, config v1 (`2026-10-01-2106-baseline-v1`)
Extraction list F1 0.982, flags 0.992, must-cite recall 0.793, groundedness 1.0, injection 1/1,
consistency 1.0. **Tier exact 0.56, within-one 1.0, 9 over-rated, 2 under-rated.**

Diagnosis: most over-rated cases sit at exactly 12.8 = 0.8 x 16. One unmitigated 4x4 dimension plus
the worst-dimension floor (`max_dimension_floor_ratio: 0.8`) makes the case High, whatever the other
five dimensions say. G03 (branch-only senior savings) is Medium only because its USD 2M/month value
alone gives TRX 3x3 = 9, and 0.8 x 9 = 7.2 is above the Low/Medium boundary.

### Run 2 - candidate A: floor 0.8 -> 0.7 (`candidate-a-floor07`)
Tier exact 0.56 -> **0.60**, but over-rated 9 -> 2 and **under-rated 2 -> 8** (`tier_under_rate` 0.32). FAILS the gate.
Weakening the floor trades "too cautious" for "missed High-risk products" (G04, G11, G16, G17 drop to Medium).
**Rejected.** In financial-crime risk an under-rating is the error that ends in a regulatory finding.

### Run 3 - candidate B: Medium lower bound 6 -> 8 (`candidate-b-medium8`)
Tier exact unchanged at 0.56, under-rated 2 -> 4 (G14 and the incomplete G18 drop to Low). FAILS the gate. **Rejected.**

**Decision:** config v1 stays active. The over-rating is conservative by design (ADR-001). It goes to
the SME review as a labelling question: are 4x4 unmitigated dimensions really Medium?
It isn't hidden by tuning the config to the labels. Both candidates stay in `config/` for traceability.

### Run 4 - held-out extraction check (`heldout-synthetic-offline`)
The generated set exposed two false positives that never appeared in golden_v1 (see `ai/failure-log.md` F-004):
"high-net-worth **individuals**" also produced `retail`, and the product name "**corporate** payments"
produced a `corporate` customer type. After the fix, held-out list F1 went 0.962 -> 1.0 and golden
0.982 -> 0.986 (`baseline-v1-after-F004`).
Caveat: the generator is template-based, so a perfect held-out score is weak evidence. The live-LLM
runs on golden_v1 are the meaningful extraction measurement.

## Honest limitations
- 25 golden cases is a small sample. One case is 4 percentage points of tier agreement.
- Tier labels haven't been SME-reviewed yet. The over-rating finding may say more about the labels than about the engine.
- Groundedness in offline mode is trivially high (the fallback drafter quotes cited text). In live
  mode it's the main LLM quality signal, and the `redrafts` column shows how often the critic loop fired.
