# ADR-002: LangGraph for runtime orchestration

Status: Accepted

## Context
The pipeline must pause for humans (G0, G1/G2), survive restarts, loop with
bounds (critique -> redraft), and route around failures. The audit needs a
precise record of which step produced what.

## Options considered
| Option | Human interrupts | Durable state | Explicit control flow | Cost |
|---|---|---|---|---|
| Plain Python functions + DB flags | manual | manual | yes | free |
| CrewAI / AutoGen role-play agents | weak | weak | emergent, hard to audit | free |
| Temporal | strong | strong | yes | heavy to operate for a 1-day build |
| **LangGraph** | `interrupt()` built in | checkpointers (SQLite/Postgres) | typed state graph | free OSS |

## Decision
LangGraph `StateGraph` with typed state, conditional edges, two interrupts, a
SQLite checkpointer locally and a Postgres checkpointer in compose. Agents are
**nodes with a single job**, not free-roaming conversational agents: an
examiner-facing system needs predictable control flow more than autonomy.

## Consequences
- Every node is an OpenTelemetry span; the graph image is the documentation.
- Free-form multi-agent debate is deliberately not used; less "agentic" but
  auditable. Accepted.
