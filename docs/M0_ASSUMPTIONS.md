# M0 assumptions and deferred items

## Assumptions made during M0

1. Python 3.12 is the baseline runtime (see `.python-version`).
2. PostgreSQL 16 is the local development database (Docker Compose service `postgres`).
3. Default local credentials are `adp` / `adp` / database `adp` (override via `.env`).
4. LangGraph is declared as a dependency for forward compatibility; no graphs are implemented in M0.
5. Application startup does not crash if PostgreSQL is temporarily unavailable; `/ready` returns 503 until the database responds.
6. The lightweight UI is a package placeholder only (`ui/static/.gitkeep`); no frontend is served in M0.
7. Packaging uses **uv** with a committed `uv.lock`. Dev tools live in the `dev` dependency group.
8. In constrained CI agent environments without Docker, integration tests and Compose validation may be deferred to a machine/CI job that provides PostgreSQL (GitHub Actions `integration` job).

## Deferred to later milestones (do not implement in M0)

| Item | Milestone |
| --- | --- |
| Canonical artefact models + ArtefactStore | M1 |
| Alembic migrations / artefact tables | M1 |
| LangGraph workflows and HITL | M2+ |
| Agents / LLM integration | M3+ |
| Review UI | M5 |
| Databricks adapter | M6 |
