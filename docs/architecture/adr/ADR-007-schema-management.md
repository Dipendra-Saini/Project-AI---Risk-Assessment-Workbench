# ADR-007: One codebase for SQLite and Postgres; Alembic baseline

Status: Accepted

## Decision
SQLAlchemy 2.0 typed models; an Alembic baseline revision creates the schema
plus audit triggers (and the `vector` extension on Postgres). Further schema
changes are incremental Alembic revisions. Developers and CI use SQLite (zero
setup); compose and cloud use Postgres + pgvector.

## Consequences
Dialect-specific bits are isolated to the embedding `TypeDecorator`, the
trigger DDL and the audit advisory lock.
