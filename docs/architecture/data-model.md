# Data model

The governed data layer the AI reasons over. Every AI output is stored next to
its provenance (model, prompt version, origin) and every human change is an
`override` row plus an audit event.

```mermaid
erDiagram
  users ||--o{ change_requests : raises
  change_requests ||--o{ documents : has
  change_requests ||--o{ extractions : "versioned extraction"
  change_requests ||--o{ assessments : "versioned assessment"
  assessments ||--o{ factor_ratings : "one per dimension"
  assessments ||--o{ assessment_controls : applies
  controls ||--o{ assessment_controls : "library item"
  change_requests ||--o{ overrides : records
  change_requests ||--o{ committee_votes : receives
  change_requests ||--o| decisions : "at most one"
  config_versions ||--o{ assessments : "scored with"
  policy_chunks }o--o{ factor_ratings : "cited by"
  change_requests ||--o{ llm_calls : "token ledger"
  audit_events }o--|| change_requests : "entity ref"

  change_requests {
    int id PK
    string ref
    string title
    string change_type
    string status
    int config_version_id FK
    bool needs_human
    int graph_run
  }
  extractions {
    int id PK
    int cr_id FK
    int version
    json data "value, confidence, span, origin per field"
    json flags "injection and span warnings"
    string prompt_version
  }
  assessments {
    int id PK
    int cr_id FK
    int version
    float inherent_overall
    float residual_overall
    string residual_tier
    json score_trace
    json narrative
    json critique
    bool narrative_signed
  }
  factor_ratings {
    int id PK
    int assessment_id FK
    string dimension
    int likelihood
    int impact
    string origin "rule, ai, human"
    json rule_ids
    json citations
    bool confirmed
  }
  overrides {
    int id PK
    string target_type
    string target_key
    json old_value
    json new_value
    string reason
    string tier_before
    string tier_after
    bool requires_ack
    int acked_by
  }
  audit_events {
    int seq PK
    string actor
    string action
    json payload
    string prev_hash
    string hash
  }
  policy_chunks {
    string id PK
    string doc_title
    json tags
    text text
    vector embedding
  }
  llm_calls {
    int id PK
    string node
    string provider
    string model
    string prompt_version
    int input_tokens
    int output_tokens
    bool cache_hit
  }
```

## Governance properties of the model
- **Versioned, never overwritten**: extractions, assessments and configs get new
  versions; old ones remain for the examiner.
- **Origin on every rating**: `rule` (with rule ids), `ai` (with model and
  citations) or `human` (with override id).
- **Config pinning**: each assessment references the config version it used.
- **Append-only audit**: DB triggers block UPDATE/DELETE; SHA-256 hash chain
  makes any out-of-band edit detectable.
- **Portable**: `embedding` is pgvector on Postgres and JSON on SQLite via one
  SQLAlchemy `TypeDecorator`.
