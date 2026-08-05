# M1 implementation summary

## Outcome

Typed domain models for the seven canonical artefacts, a PostgreSQL-backed `ArtefactStore`, lightweight SQL migrations, append-only audit events, lineage edges, and `/dev/...` persistence APIs — proving versioned artefact persistence and audit without agents, LangGraph, or HITL.

## Delivered

| Deliverable | Location / notes |
| --- | --- |
| Seven artefact payload models | `domain/artefacts.py` — Business Requirement through Review Package |
| Run / audit / lineage types | `domain/run.py`, `domain/audit.py`, `domain/lineage.py`, `domain/enums.py` |
| `ArtefactStore` + `PostgresArtefactStore` | `persistence/store.py` |
| ORM tables | `persistence/models.py` — `workflow_runs`, `artefacts`, `audit_events`, `lineage_edges` |
| Lightweight migrations | `persistence/migrate.py` + `persistence/migrations/versions/001_m1_tables.sql` (`schema_migrations`) |
| Dev persistence APIs | `app/routes/dev.py` — `/dev/runs`, `/dev/artefacts`, `/dev/lineage`, `/dev/audit` |
| Unit tests | `tests/unit/test_artefact_schemas.py` |
| Integration tests | `tests/integration/test_persistence_crud.py` |
| Makefile targets | `db`, `migrate`, `verify`, `dev` |
| CI | Integration job runs migrate before pytest |

## Behaviour highlights

- Unique constraint on `(run_id, artefact_type, version)`
- Same `artefact_id` reused across versions of a type within a run; version auto-increments when omitted
- Audit events written on run, artefact, and lineage creation
- Invalid artefact payloads return HTTP **422** from `/dev/artefacts` (validated before store I/O)

## Explicitly not delivered (by design)

- LangGraph checkpointer / workflows
- HITL review APIs (Approve / Reject / Request revisions)
- Agents, LLM providers, consultant UI
- Databricks / platform adapters
- Alembic (lightweight SQL runner used instead for M1)
