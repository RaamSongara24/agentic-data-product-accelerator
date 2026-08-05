# M0 known limitations

1. **No schema / migrations** — Postgres is used only for connectivity (`SELECT 1`). Tables arrive in M1.  
2. **No orchestration** — LangGraph is installed but unused; no checkpointer, graphs, or HITL.  
3. **No auth / RBAC** — Consistent with MVP product stance (no app RBAC); not in M0 scope.  
4. **UI not served** — `ui/static/.gitkeep` only; no static mount or review screens.  
5. **Local credentials** — Compose defaults are for development only; production secrets are out of scope.  
6. **Settings cache** — `get_settings()` is process-cached; tests clear the cache explicitly.  
7. **Integration tests require Postgres** — Locally via Compose; in CI via the `integration` job service container.  
8. **Docs layout** — Product docs remain at repository root (`PRODUCT_SPEC.md`, etc.); milestone evidence lives under `docs/milestones/`.

Deferred work is tabulated in [`docs/M0_ASSUMPTIONS.md`](../../M0_ASSUMPTIONS.md).
