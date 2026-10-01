# Risk Assessment Workbench - Specification v1.0

Expanded from `00-brief.md`. Every requirement is testable and traced to user
stories (`user-stories.md`), tests and evals. Gaps in the brief and the
assumptions taken are listed in `assumptions.md`.

## 1. Goals and success measures

| Goal (from brief) | Measure | Target | How we measure |
|---|---|---|---|
| Intake to decision-ready in ~2 days | Elapsed time from `Submitted` to `CommitteeReview` | p50 <= 2 business days | `case_stage_seconds` metric, Grafana |
| Consistency between analysts | Same inputs -> same tier | 100% for deterministic scoring; >= 95% tier agreement across 3 AI re-runs | `evals/` consistency suite |
| Traceability | Every rating has inputs, rule/AI origin, citations, config version | 100% of ratings | API test + examiner pack check |
| Examiner-ready audit | Tamper-evident trail per case | Hash chain verifies | `/api/audit/verify` |
| Humans decide | Zero automated terminal decisions | 0 | invariant test + audit query |

## 2. Personas

| Persona | Goal | Pain today | Gets in RAW |
|---|---|---|---|
| **Priya - Product Owner** (business unit) | Launch her change fast | Does not know what FCRM needs; back-and-forth by email | Guided intake, document upload, AI pre-fills the form, live status |
| **Arjun - FCRM Analyst** | Defensible assessment, quickly | Re-reads policy each time, rebuilds spreadsheets | Pre-scored draft with citations, override with reason, config ownership |
| **Committee (Chair Meera + members)** | Decide with full picture | Long Word memos, unclear rationale | One-page decision pack, voting, conditions |
| **Examiner** (secondary) | Reconstruct "why" months later | Scattered emails | Examiner pack export with verified hash chain |

## 3. Scope

In scope: intake, document extraction, policy retrieval, inherent/control/residual
scoring, narrative drafting, analyst review and override, committee voting and
decision with conditions, configuration, audit and export, observability, evals.

Out of scope (v1): SSO integration (seeded users + JWT instead), e-mail
notifications (in-app status only), post-launch condition monitoring workflow
(conditions are captured and exported only), integration with real bank systems
(prohibited by the brief).

## 4. Functional requirements

### Intake
- **FR-01** A product owner can create a change request with title, description, change type (new product, product feature change, process change, vendor onboarding, new geography, new customer segment), business line, target launch date, and attachments (PDF/DOCX/TXT/MD).
- **FR-02** The system extracts structured attributes from the description and attachments (customer types, geographies, channels, expected volumes/values, third parties, cash/crypto/cross-border exposure). Each extracted value carries a source span and a confidence.
- **FR-03** The product owner reviews the extraction, corrects it, and confirms (gate **G0**) before submission. Corrections are logged as overrides.

### Assessment
- **FR-04** On submission the system runs the assessment pipeline: classify, extract, retrieve policy, rate factors, score, draft, critique.
- **FR-05** Factor ratings (likelihood, impact) per dimension are produced by deterministic rules when a rule matches; otherwise an AI suggestion is produced, flagged `origin=ai`, with a citation.
- **FR-06** Controls are selected from a control library; each has design and operating effectiveness (0-1). Residual risk is computed deterministically and is always > 0 and <= inherent.
- **FR-07** The system retrieves the most relevant policy/framework passages per dimension and shows them with ids.
- **FR-08** The system drafts an assessment narrative per dimension in which every sentence cites a retrieved passage; a critic flags unsupported claims.
- **FR-09** The pipeline is resumable: a failure mid-run does not lose state; failed steps route the case to `needs_human` with a reason.

### Analyst review
- **FR-10** The analyst can accept or override any system output (extracted field, factor rating, control effectiveness, narrative). Overrides require a reason (min 15 characters).
- **FR-11** After an override, scores recompute immediately. If the residual tier changes, a second analyst must acknowledge before committee submission.
- **FR-12** Gate **G1**: all AI-suggested factors must be explicitly accepted or overridden. Gate **G2**: the narrative must be signed off; unresolved critic warnings require a reason.
- **FR-13** The analyst can send the case back to the product owner with an information request, or re-run the pipeline.

### Committee
- **FR-14** Committee members see a decision pack: summary, scores, trace, overrides, citations, critic warnings.
- **FR-15** Each member votes Approve / Approve with conditions / Reject / Defer with a rationale and a conflict-of-interest declaration. Members with a conflict cannot vote.
- **FR-16** A decision is recorded only when quorum (configurable, default 3) is met; the outcome is the majority, ties resolve to Defer. Conditions are captured as free text items.
- **FR-17** No API, job or agent can move a case to a terminal state except the committee decision function.

### Configuration
- **FR-18** The analyst can edit scoring weights, thresholds, mitigation cap, floor ratio and quorum. Each save creates a new immutable config version; open cases keep the version they were scored with unless re-scored explicitly.

### Audit and export
- **FR-19** Every state change, AI output, override, vote, config change and export is written to an append-only, hash-chained audit log.
- **FR-20** Anyone with audit access can verify chain integrity.
- **FR-21** An examiner pack (JSON + printable HTML) can be exported per case with all inputs, outputs, citations, overrides, votes, config version and chain proof.

## 5. Non-functional requirements

- **NFR-01 Security**: JWT auth, role-based access per endpoint, no secrets in repo, uploaded files size-limited (5 MB) and type-checked; uploaded text is treated as untrusted (prompt-injection guard: documents are passed as data in a delimited block, instructions in them are ignored, and the extraction schema is validated).
- **NFR-02 Reliability**: LLM calls have timeouts, bounded retries, provider fallback and a circuit breaker; if all fail, the case degrades to rules-only scoring + template narrative, never blocks.
- **NFR-03 Performance**: API p95 < 300 ms excluding pipeline; pipeline < 60 s per case on free tiers.
- **NFR-04 Cost**: <= 12k LLM tokens per case (budget enforced); zero tokens in CI.
- **NFR-05 Observability**: traces per pipeline node, Prometheus metrics, token ledger.
- **NFR-06 Portability**: runs on SQLite (laptop) and Postgres + pgvector (compose/cloud) with the same code.
- **NFR-07 Data**: synthetic only.
- **NFR-08 Accessibility**: keyboard navigable UI, semantic HTML, colour is never the only signal for a tier.

## 6. Automation split (the "deliberately not specified" decisions)

| Activity | Mode | Why |
|---|---|---|
| Workflow routing and state | Deterministic | Must be predictable and auditable |
| Change-type classification | Rules, AI fallback | Form field is usually enough; AI only for "other" |
| Extraction from documents | **AI** (small model) + schema validation | Unstructured text; checkable via G0 |
| Policy retrieval | Deterministic (BM25 + embeddings) | Ranking, no generation needed |
| Factor rating | Rules first, **AI suggestion** for gaps | Rules give consistency; AI covers the long tail, human confirms |
| Scoring | Deterministic | Must be reproducible and tunable |
| Narrative | **AI** (larger model) + critic | Drafting prose is where AI earns its place |
| Final assessment | Human (analyst) | Accountability |
| Decision | Human (committee) | Brief: "humans decide" |
