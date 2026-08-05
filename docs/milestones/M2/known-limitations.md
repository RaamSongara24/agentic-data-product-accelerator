# M2 known limitations

1. **Stub generator only** — no LLM; Business Requirement content is deterministic / optional seed payload.
2. **Single HITL gate** — one artefact stage; multi-stage reviews arrive in M3+.
3. **In-process execution** — graph runs in the API process; no separate worker or queue.
4. **No UI** — review is API-only until M5.
5. **Checkpointer schema** — managed by LangGraph `AsyncPostgresSaver.setup()`, separate from app SQL migrations under `persistence/migrations/`.
6. **No authn** — reviewer_id is optional client-supplied metadata (no app RBAC per product decision).
