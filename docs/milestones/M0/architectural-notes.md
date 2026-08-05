# M0 architectural notes

## Product framing

This codebase scaffolds an **Agentic Data Product Design Platform** (canonical artefacts + HITL review). It is **not** a Databricks code generator. Databricks remains a future **adapter** (M6), not core identity.

## Package layout vs ARCHITECTURE.md

[`ARCHITECTURE.md`](../../../ARCHITECTURE.md) §13 suggests top-level packages under `src/`. M0 places them under the installable package `src/agentic_data_product/` so imports, typing (`py.typed`), and hatchling packaging stay coherent.

| Package | M0 role |
| --- | --- |
| `app` | FastAPI factory, lifespan, health routes |
| `config` | pydantic-settings |
| `observability` | Logging setup (text/JSON) — practical addition beyond the abbreviated diagram |
| `persistence` | Async engine + ping only |
| `orchestration` | Empty stub (LangGraph workflows from M2) |
| `domain` | Empty stub (artefacts from M1) |
| `integrations` | Empty stub |
| `adapters` | Empty stub (Databricks from M6) |
| `ui` | Placeholder (`static/.gitkeep`; UI from M5) |

## Process model

- **Lifespan** creates the `Database` wrapper and attempts connect at startup.  
- Startup **does not crash** if Postgres is down; `/ready` returns 503 until connectivity works.  
- `/health` is process liveness only (no dependency checks).

## Tooling alignment

- **uv** + committed lockfile for reproducible installs.  
- **Ruff** for lint/format; **Mypy** strict on `src`.  
- **Pytest** splits unit (ASGI, no DB) vs integration (real Postgres).  
- **Compose**: Postgres always; API optional for full-stack demos.
