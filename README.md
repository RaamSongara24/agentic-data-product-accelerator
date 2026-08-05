# Agentic Data Product Accelerator

**Agentic Data Product Design Platform** — transform business requirements into governed, technology-agnostic data product designs through multi-agent orchestration and human-in-the-loop review.

| | |
| --- | --- |
| **Status** | Milestone **M1** complete (domain model + persistence) |
| **MVP target** | September 2026 |
| **Primary MVP user** | Data Consultant |
| **Stack** | Python 3.12 · uv · FastAPI · LangGraph (dep only) · PostgreSQL |

---

## Overview

The accelerator helps teams design analytics-ready data products faster. AI agents will produce a **canonical data product model**; humans approve each stage before the workflow continues. Platform-specific assets (for example Databricks pipelines) are generated later via **adapters**.

**M0–M1 scope:** production-quality skeleton plus typed canonical artefacts, ArtefactStore, audit/lineage persistence, and `/dev` validation APIs. No agents, graphs, HITL, or adapters yet.

Full product intent: [`PRODUCT_SPEC.md`](PRODUCT_SPEC.md).

---

## Vision and purpose

- Accelerate delivery and reduce technical bottlenecks in data product design.  
- Keep engineers and consultants as **reviewers**; agents as **builders** of canonical artefacts.  
- Remain **technology agnostic**: Databricks is the first adapter target for availability — not because the platform is Databricks-native.  
- Respect the **authenticated user’s** source-platform permissions; never bypass or elevate access.

---

## High-level architecture

```mermaid
flowchart TB
  UI[LightweightReviewUI] --> API[FastAPI]
  API --> LG[LangGraphOrchestrator]
  LG --> Store[CanonicalArtefacts]
  LG --> PG[(PostgreSQL)]
  Store --> PG
  Store --> DBX[DatabricksAdapter]
  Store --> FUT[FutureAdapters]
```

Layers: **AI execution** (UI, API, LangGraph) → **canonical model** → **platform adapters**. Details: [`ARCHITECTURE.md`](ARCHITECTURE.md).

**M0–M1 implements:** FastAPI + config + logging + PostgreSQL schema (runs, artefacts, audit, lineage) + ArtefactStore + `/health` + `/ready` + `/dev` persistence APIs.

---

## Core concepts

| Concept | Meaning |
| --- | --- |
| **Canonical artefact** | Technology-agnostic, versioned definition of part of a data product |
| **HITL** | Workflow review point after each generated artefact |
| **Adapter** | Maps approved canonical artefacts to a target platform |
| **Artefact store** | Persistence abstraction (PostgreSQL in MVP; object storage later) |
| **Run** | One LangGraph execution thread (`run_id` = checkpointer `thread_id`) |

---

## Seven canonical artefacts

1. **Business Requirement**  
2. **Technical Requirement**  
3. **Semantic Model**  
4. **Data Model**  
5. **Pipeline Specification**  
6. **Metric Definitions**  
7. **Review Package**  

See [`PRODUCT_SPEC.md`](PRODUCT_SPEC.md) §5. Models and persistence are delivered in **M1** (complete).

---

## Human-in-the-loop workflow

| Decision | Effect |
| --- | --- |
| **Approve** | Continue to the next stage |
| **Reject** | Terminate the workflow |
| **Request revisions** | Regenerate the current artefact; review again |

Implemented from **M2** onward. See [`adr/005-human-in-the-loop-workflow.md`](adr/005-human-in-the-loop-workflow.md).

---

## Technology stack

| Concern | Choice |
| --- | --- |
| Language / packaging | Python 3.12, **uv** |
| API | **FastAPI** + Uvicorn |
| Orchestration | **LangGraph** (dependency reserved; workflows from M2) |
| Persistence | **PostgreSQL** 16 + SQLAlchemy async + asyncpg |
| Quality | Ruff, Mypy, Pytest, Pre-commit, GitHub Actions |

---

## Current status

| Area | Status |
| --- | --- |
| Documentation baseline | Complete |
| **M0 scaffolding** | **Complete** — evidence in [`docs/milestones/M0/`](docs/milestones/M0/) |
| **M1 domain + persistence** | **Complete** — evidence in [`docs/milestones/M1/`](docs/milestones/M1/) |
| M2+ application features | Not started |

Assumptions: [`docs/M0_ASSUMPTIONS.md`](docs/M0_ASSUMPTIONS.md). Milestone close-out: [`docs/milestones/M0/`](docs/milestones/M0/), [`docs/milestones/M1/`](docs/milestones/M1/).

---

## Repository structure

```text
.
├── adr/
├── docs/
│   └── milestones/M0/, M1/
├── src/agentic_data_product/
│   ├── app/                 # FastAPI (health/ready + /dev persistence)
│   ├── config/              # pydantic-settings
│   ├── observability/       # logging setup
│   ├── persistence/         # DB, migrations, ArtefactStore
│   ├── orchestration/       # reserved (M2+)
│   ├── domain/              # canonical artefact + run/audit/lineage models
│   ├── integrations/        # reserved
│   ├── adapters/            # reserved (M6)
│   └── ui/                  # reserved (M5)
├── tests/unit/
├── tests/integration/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── .github/workflows/ci.yml
```

---

## Quick start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker + Docker Compose (for PostgreSQL)

### 1. Install dependencies

```bash
cp .env.example .env
uv sync --group dev
```

### 2. Start PostgreSQL and migrate

```bash
make db
make migrate
```

Equivalent: `docker compose up -d postgres` then `uv run python -m agentic_data_product.persistence.migrate`.

### 3. Run the API

```bash
uv run uvicorn agentic_data_product.app.main:app --reload --host 0.0.0.0 --port 8000
```

Or: `make run` / `make dev`

### 4. Health endpoints

```bash
curl -s http://127.0.0.1:8000/health | python3 -m json.tool
curl -s http://127.0.0.1:8000/ready | python3 -m json.tool
```

- `GET /health` — process liveness (always 200 if the app is up)  
- `GET /ready` — PostgreSQL readiness (`200` ready / `503` unavailable)

### 5. Dev persistence APIs (M1)

```bash
# Create a run, save an artefact version, inspect audit/lineage
curl -s -X POST http://127.0.0.1:8000/dev/runs -H 'content-type: application/json' \
  -d '{"title":"demo"}' | python3 -m json.tool
```

Routes: `POST/GET /dev/runs`, `POST/GET /dev/artefacts`, `POST/GET /dev/lineage`, `GET /dev/audit`.

### 6. Tests and quality

```bash
make verify   # lint, format check, mypy, unit + integration (requires Postgres + migrate)
```

Or individually:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest tests/unit -q
uv run pytest tests/integration -q -m integration
```

### 7. Full stack via Docker Compose

```bash
docker compose up --build
```

API: http://localhost:8000/health

### 8. Pre-commit (optional local hooks)

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

---

## Roadmap

| Milestone | Focus |
| --- | --- |
| **M0** | Scaffold: uv, FastAPI, Postgres connectivity — **complete** |
| **M1** | Artefact schemas, ArtefactStore, audit/lineage — **complete** |
| **M2** | LangGraph + HITL skeleton |
| **M3–M7** | Agents, UI, adapter, demo |

See [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md).

---

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Architecture decisions: [`adr/`](adr/).

---

## Documentation index

| Document | Purpose |
| --- | --- |
| [`PRODUCT_SPEC.md`](PRODUCT_SPEC.md) | What we build |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | How we build it |
| [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) | Milestones |
| [`docs/M0_ASSUMPTIONS.md`](docs/M0_ASSUMPTIONS.md) | M0 assumptions |
| [`docs/milestones/M0/`](docs/milestones/M0/) | M0 close-out evidence |
| [`docs/milestones/M1/`](docs/milestones/M1/) | M1 close-out evidence |
| [`adr/`](adr/) | Decision records |

---

## License

See [`LICENSE`](LICENSE) (placeholder until SPDX license is confirmed).
