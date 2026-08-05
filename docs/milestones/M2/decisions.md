# M2 decisions

| ID | Decision | Rationale |
| --- | --- | --- |
| D1 | In-process graph execution inside FastAPI lifespan | Sufficient for M2; worker process deferred (ARCHITECTURE §16 open item) |
| D2 | `AsyncPostgresSaver` + psycopg connection pool | Official LangGraph Postgres checkpointer; survives API restart |
| D3 | Stub generator writes **Business Requirement** via ArtefactStore | Matches first stage of the canonical pipeline; no LLM in M2 |
| D4 | LangGraph `interrupt()` + `Command(resume=…)` | Native durable HITL; maps cleanly to Approve / Reject / Request revisions |
| D5 | `run_id` string as checkpointer `thread_id` | Aligns with ARCHITECTURE §8 and ADR 003 |
| D6 | Application `workflow_runs.status` synced from graph snapshot after each invoke | APIs expose product statuses without requiring clients to read checkpoint tables |
| D7 | Keep `/dev/...` M1 APIs alongside production `/runs` | Dev store validation remains useful; production contracts live at `/runs` |
