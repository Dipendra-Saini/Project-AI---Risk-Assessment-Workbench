# Failure log

Every time an agent (build-time or runtime) failed, stalled or produced something
wrong, it is recorded here: what happened, how it was detected, how we
recovered, and what changed in the harness so it does not recur.

| Id | Stage | Symptom | Detection | Recovery | Harness change |
|---|---|---|---|---|---|
| F-001 | Setup | Agent tried to create the Python venv and failed with `Operation not permitted` | Shell exit code + error text | Re-ran with explicit elevated permission for that one command | `AGENTS.md` "Commands" section now documents `make setup` as the single setup entry point so agents do not improvise |
| F-003 | Development (runtime harness) | All API tests passed on first run, but inspecting golden case G01 showed residual tier High where the golden label is Medium. Root causes in the deterministic extractor: "platform companies" matched the `corporate` keyword (false customer type), and a controls sentence that wrapped onto a second line was cut, so the velocity limit never mapped to C-LIM-01 and Products risk kept zero mitigation | Human inspection of the full assessment dump (`RAW_INSPECT=1 pytest tests/api/test_inspect_output.py`) against the golden facts - green tests were not trusted on their own | Removed the over-broad keyword; sentence splitter now joins line-wraps within a paragraph; control phrases split on `,`/`;` only (not inside numbers like `2,000`) | Added the inspection helper to the workflow and made golden-set evals (extraction F1 + tier agreement) a CI gate so this class of error is caught by numbers, not by luck |
| F-002 | Setup | `git` unavailable on the build Mac (Xcode Command Line Tools missing) - agent could not commit, and commit history is a judged artefact | `xcode-select` error on first `git status` | Triggered CLT install for the human; agent committed through `dulwich` (pure-Python git, standard `.git` format) until native git was available | Setup checklist in README lists git as a prerequisite |
