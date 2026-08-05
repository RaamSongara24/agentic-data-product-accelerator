# M0 decisions

These decisions apply to the scaffolding only. Product decisions already settled in ADRs / PRODUCT_SPEC are not reopened here.

| ID | Decision | Rationale |
| --- | --- | --- |
| D1 | Installable package name `agentic_data_product` under `src/` | Clear imports and packaging; matches ARCHITECTURE layers as subpackages |
| D2 | PostgreSQL 16 via Docker Compose with local defaults `adp`/`adp`/`adp` | Matches IMPLEMENTATION_PLAN; documented in `.env.example` |
| D3 | `/health` = liveness; `/ready` = DB ping | Standard k8s-style probes; API can boot before DB is ready |
| D4 | LangGraph listed as a runtime dependency with no graphs | Reserves the stack for M2 without implementing workflows early |
| D5 | Dev tools in uv `dependency-groups.dev` | Separates prod image (`uv sync --no-dev`) from developer/CI tooling |
| D6 | CI: quality → integration + docker | Unit gate first; Postgres and image build as dependent jobs |
| D7 | No Alembic / schema in M0 | Connectivity only; migrations belong to M1 with ArtefactStore |
| D8 | Evidence under `docs/milestones/M0/` | Durable close-out record separate from product ADRs |

Assumptions that informed these choices: [`docs/M0_ASSUMPTIONS.md`](../../M0_ASSUMPTIONS.md).
