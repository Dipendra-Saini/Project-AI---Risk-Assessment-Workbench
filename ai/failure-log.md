# Failure log

Every time an agent (build-time or runtime) failed, stalled or produced something
wrong, it is recorded here: what happened, how it was detected, how we
recovered, and what changed in the harness so it does not recur.

| Id | Stage | Symptom | Detection | Recovery | Harness change |
|---|---|---|---|---|---|
| F-001 | Setup | Agent tried to create the Python venv and failed with `Operation not permitted` | Shell exit code + error text | Re-ran with explicit elevated permission for that one command | `AGENTS.md` "Commands" section now documents `make setup` as the single setup entry point so agents do not improvise |
| F-002 | Setup | `git` unavailable on the build Mac (Xcode Command Line Tools missing) - agent could not commit, and commit history is a judged artefact | `xcode-select` error on first `git status` | Triggered CLT install for the human; agent committed through `dulwich` (pure-Python git, standard `.git` format) until native git was available | Setup checklist in README lists git as a prerequisite |
