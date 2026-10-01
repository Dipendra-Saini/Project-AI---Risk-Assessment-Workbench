# ADR-005: Append-only, hash-chained audit log in the primary database

Status: Accepted

## Context
"An immutable audit trail that can be handed to an examiner."

## Options
- Application logs: mutable, not queryable per case.
- External ledger / blockchain: operational overhead, no added value inside one bank.
- WORM object storage: good in production, not free locally.
- **Append-only table + DB triggers + SHA-256 hash chain**: chosen.

## Decision
`audit_events(seq, ts, actor, action, entity_type, entity_id, payload, prev_hash, hash)`
with `hash = sha256(prev_hash || canonical_json(event))`. Triggers reject
UPDATE/DELETE on both SQLite and Postgres. `/api/audit/verify` recomputes the
chain and returns the first broken `seq`. The examiner pack embeds the case's
events plus the chain head hash.

## Consequences
Tampering by a DBA who drops the trigger is still *detectable*. Production
hardening path: periodically anchor the head hash to WORM storage.
