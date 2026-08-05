# M2 implementation summary

Durable human-in-the-loop interrupt/resume on a **stub** Business Requirement artefact, using LangGraph with a PostgreSQL checkpointer and production run/review APIs.

## Delivered

| Area | Detail |
| --- | --- |
| HITL stub graph | `orchestration/graph.py` — `generate_stub` → `await_review` (`interrupt`) → approve / terminate / regenerate |
| Postgres checkpointer | `langgraph-checkpoint-postgres` `AsyncPostgresSaver` via psycopg pool; `thread_id` = `run_id` |
| Runner | `orchestration/runner.py` — starts runs, applies reviews, syncs `workflow_runs.status` |
| Production APIs | `POST /runs`, `GET /runs/{id}`, `POST /runs/{id}/reviews` |
| Store extensions | `update_run_status`, `record_review`; audit actions `run_status_updated`, `review_submitted` |
| Domain | `ReviewDecisionKind`, `ReviewDecisionRequest`, `PendingReview`, `RunDetail`, `CreateRunApiRequest` |
| Tests | Unit routing + checkpointer URL; integration for approve / reject / request_revisions + restart durability |
| Dev APIs | Unchanged `/dev/...` from M1 |

## HITL semantics (ADR 005)

| Decision | Effect |
| --- | --- |
| **Approve** | Graph advances to terminal `approved`; run status `approved` |
| **Reject** | Graph advances to terminal `terminated`; run status `terminated` |
| **Request revisions** | Feedback stored; stub generator writes a new artefact version; returns to `waiting_for_review` |

## Out of scope (as planned)

- Real LLM Requirements / Modelling agents (M3–M4)
- Mapping / discovery subgraph
- Consultant UI (M5)
- Platform adapters (M6)
