# Assumptions and open questions

The brief is deliberately incomplete. Each gap below records the assumption we
took, why, and what breaks if it is wrong. No clarification was available, so
these are decisions we defend rather than wait on.

| # | Gap in brief | Assumption | Rationale | Risk if wrong / mitigation |
|---|---|---|---|---|
| A-01 | What "decision-ready" means | Case reached `CommitteeReview` with G0-G2 passed | Committee scheduling is outside the system's control | Metric could look better than reality; we also track total time to decision |
| A-02 | Scoring scale | 1-5 likelihood x 1-5 impact per dimension (1-25) | Most common in bank RCSA practice, easy for committees to read | Tunable in config; scale change needs a migration of thresholds only |
| A-03 | How dimensions combine | Weighted mean with a "max-dimension floor" (overall >= 80% of the worst dimension) | Pure averages hide a single critical exposure, which examiners criticise | Floor ratio is configurable |
| A-04 | How controls reduce risk | Effectiveness = design x operating; mitigation capped at 70%; residual floor 20% of inherent | Brief: controls never eliminate risk | Cap/floor configurable; property tests enforce the invariant |
| A-05 | Committee size and quorum | Quorum 3, simple majority, ties -> Defer | Defer is the safe outcome when the committee is split | Configurable |
| A-06 | Who can override what | PO: extraction only (pre-submit). Analyst: everything pre-committee. Committee: no score edits, only vote and conditions | Separation of duties | Enforced by RBAC tests |
| A-07 | When a second analyst is required | Only when an override changes the residual tier | Balances control with speed (2-day target) | Configurable flag `second_analyst_on_tier_change` |
| A-08 | Which policies exist | We author a synthetic internal policy set (AML, Sanctions, Fraud, ABC, Third-party, New Products) that cites public frameworks | Synthetic-data constraint | Real bank would ingest its own policy library via the same pipeline |
| A-09 | Jurisdiction lists | Fictional countries tagged with list categories modelled on FATF/OFAC list structure | Synthetic-data constraint, no political content | Swap the YAML for real lists in production |
| A-10 | Authentication | Seeded users, JWT, role claim | No real IdP allowed | SSO is a drop-in at the auth dependency |
| A-11 | Re-assessment after approval | Out of scope; conditions are exported | Five-week brief, one-day build | Listed in roadmap |
| A-12 | LLM provider | Free tiers (Gemini, Groq); offline deterministic provider when no key | "Free tools only" constraint; demo must never fail | Provider is behind one interface |
| A-13 | Document formats | PDF, DOCX, TXT, MD up to 5 MB | Covers typical business submissions | Extend parser registry |

## Open questions we would ask the client
1. Does the committee ever delegate low-residual cases to a single approver? (We assume no.)
2. Should risk appetite thresholds differ by business line? (Config supports per-line weights later.)
3. Retention period for the audit trail? (Assumed 7 years; storage is append-only so any period works.)
