# M1 known limitations

1. **No LangGraph / HITL** — runs are metadata rows only; no checkpointer, interrupts, or review decisions.
2. **Dev APIs only** — `/dev/...` is for validation; production run/review routes arrive in M2+.
3. **Lightweight migrations** — no Alembic autogenerate, downgrade, or multi-env migration branching.
4. **No soft delete / artefact immutability enforcement beyond insert** — versions are append-only by convention and unique constraint; no update API.
5. **No object-storage backend** — Postgres JSONB only (ArtefactStore abstraction ready for a future backend).
6. **Payload schemas are initial field sets** — not the final production richness for all seven artefacts.
7. **No RBAC / authn on `/dev`** — intentional for local/dev validation; do not expose without controls.
