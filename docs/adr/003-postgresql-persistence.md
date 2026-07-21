# ADR 003 — PostgreSQL persistence and durable checkpointer

| Field | Value |
| --- | --- |
| **ADR** | 003 |
| **Title** | PostgreSQL for application data and LangGraph checkpointing |
| **Status** | Accepted |
| **Date** | 2026-07-20 |

## Context

HITL workflows may pause for hours. Runs need durable state, audit trails, lineage, and versioned artefacts. The architecture must allow larger payloads to move to object storage later without changing agent behaviour.

See [`PRODUCT_SPEC.md`](../PRODUCT_SPEC.md) §4.4 and [`ARCHITECTURE.md`](../ARCHITECTURE.md) §5.

## Decision

- **PostgreSQL** is the primary application database.  
- LangGraph uses a **PostgreSQL checkpointer** for durable execution and HITL resume.  
- For MVP, **canonical artefacts, workflow metadata, audit, and lineage** are stored in PostgreSQL.  
- Access artefact payloads through an **ArtefactStore abstraction** so a future object-storage backend can be introduced without changing agents.

`run_id` aligns with the LangGraph `thread_id`.

## Consequences

- Single operational datastore for MVP simplifies deployment.  
- Checkpoint + artefact consistency must be designed carefully (transactions/outbox where needed).  
- Large artefacts may pressure row/JSONB size over time — abstraction enables migration.  
- Local dev depends on Postgres (e.g. Docker Compose).

## Alternatives Considered

| Alternative | Why not chosen |
| --- | --- |
| In-memory / SQLite checkpointer only | Insufficient for shared durable HITL |
| Object storage for all artefacts from day one | Extra complexity before volume justifies it |
| Separate DB for checkpoints vs app data | Unnecessary ops overhead for MVP |
