# Agentic Data Product Accelerator

**Agentic Data Product Design Platform** — transform business requirements into governed, technology-agnostic data product designs through multi-agent orchestration and human-in-the-loop review.

| | |
| --- | --- |
| **Status** | Milestone **M7** complete — September 2026 MVP demonstration ready |
| **MVP target** | September 2026 |
| **Primary MVP user** | Data Consultant |
| **Stack** | Python 3.12 · uv · FastAPI · LangGraph · PostgreSQL |

---

## Overview

The accelerator helps teams design analytics-ready data products faster. AI agents will produce a **canonical data product model**; humans approve each stage before the workflow continues. Platform-specific assets (for example Databricks pipelines) are generated later via **adapters**.

**M0–M7 scope:** production skeleton through full seven-artefact HITL path, lightweight consultant review UI, Databricks `PlatformAdapter` export stub (no live deploy), and MVP demo / DoD close-out. No live source connectors yet.

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

**M0–M7 implements:** FastAPI + config + logging + PostgreSQL + ArtefactStore + seven-artefact HITL graph + LLM/discovery integrations + `/health` + `/ready` + `/runs` (+ artefacts/events/lineage/export) + `/config/profile` + `/ui` review workspace + `/dev` persistence APIs.

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

Implemented in **M2** (complete). See [`adr/005-human-in-the-loop-workflow.md`](adr/005-human-in-the-loop-workflow.md) and [`docs/milestones/M2/`](docs/milestones/M2/).

---

## Technology stack

| Concern | Choice |
| --- | --- |
| Language / packaging | Python 3.12, **uv** |
| API | **FastAPI** + Uvicorn |
| Orchestration | **LangGraph** + PostgreSQL checkpointer (M4 seven-artefact HITL path) |
| Persistence | **PostgreSQL** 16 + SQLAlchemy async + asyncpg |
| Quality | Ruff, Mypy, Pytest, Pre-commit, GitHub Actions |

---

## Current status

| Area | Status |
| --- | --- |
| Documentation baseline | Complete |
| **M0 scaffolding** | **Complete** — evidence in [`docs/milestones/M0/`](docs/milestones/M0/) |
| **M1 domain + persistence** | **Complete** — evidence in [`docs/milestones/M1/`](docs/milestones/M1/) |
| **M2 HITL skeleton** | **Complete** — evidence in [`docs/milestones/M2/`](docs/milestones/M2/) |
| **M3 requirements + mapping** | **Complete** — evidence in [`docs/milestones/M3/`](docs/milestones/M3/) |
| **M4 modelling + Review Package** | **Complete** — evidence in [`docs/milestones/M4/`](docs/milestones/M4/) |
| **M5 lightweight UI + observability** | **Complete** — evidence in [`docs/milestones/M5/`](docs/milestones/M5/) |
| **M6 adapter boundary + hardening** | **Complete** — evidence in [`docs/milestones/M6/`](docs/milestones/M6/) |
| **M7 MVP demo + DoD** | **Complete** — evidence in [`docs/milestones/M7/`](docs/milestones/M7/) |

Assumptions: [`docs/M0_ASSUMPTIONS.md`](docs/M0_ASSUMPTIONS.md). Milestone close-out: [`docs/milestones/M0/`](docs/milestones/M0/) … [`docs/milestones/M7/`](docs/milestones/M7/).

---

## Repository structure

```text
.
├── adr/
├── docs/
│   └── milestones/M0/ … M7/
├── src/agentic_data_product/
│   ├── app/                 # FastAPI (health/ready + /runs + /config + /ui + /dev)
│   ├── config/              # pydantic-settings (incl. LLM + mapping caps)
│   ├── observability/       # logging setup + error taxonomy
│   ├── persistence/         # DB, migrations, ArtefactStore
│   ├── orchestration/       # LangGraph M4 graph + checkpointer + runner
│   ├── agents/              # Requirements / modelling / engineer / metrics / RP
│   ├── domain/              # canonical artefact + run/audit/lineage/review models
│   ├── integrations/        # LLM clients + fixture discovery
│   ├── adapters/            # PlatformAdapter + Databricks export stub
│   └── ui/                  # lightweight consultant review UI (static)
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

### Environment variables

Copy [`.env.example`](.env.example) to `.env`. Common settings:

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_NAME` | `agentic-data-product` | Service name |
| `APP_ENV` | `development` | Environment label (enables reload when `development`) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_JSON` | `false` | Structured JSON logs when `true` |
| `API_HOST` / `API_PORT` | `0.0.0.0` / `8000` | Bind address |
| `DATABASE_URL` | `postgresql+asyncpg://adp:adp@localhost:5432/adp` | App DB + LangGraph checkpointer |
| `LLM_PROVIDER` | `deterministic` | `deterministic` (offline demo) or `openai_compatible` |
| `LLM_API_KEY` | _(empty)_ | Required only for `openai_compatible` |
| `LLM_MODEL` | `gpt-4o-mini` | Model id for compatible provider |
| `LLM_BASE_URL` | OpenAI URL | Compatible API base |
| `LLM_TIMEOUT_SECONDS` | `60` | LLM HTTP timeout |
| `MAPPING_SCHEMA_RETRY_CAP` | `2` | Mapping judge schema retry cap |
| `MAPPING_LOGIC_RETRY_CAP` | `2` | Mapping judge logic retry cap |

Secrets stay in env only — never committed or stored in graph state.

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

### 4. Consultant review UI + MVP demo (M5–M7)

Open [http://127.0.0.1:8000/ui/](http://127.0.0.1:8000/ui/) (root `/` redirects there).

Submit a Business Requirement, track run progress, review artefact payloads, and use **Approve** / **Reject** / **Request revisions**. After approval, inspect **audit events**, **lineage**, and optionally run the **Databricks export stub** (not a live deploy).

**Stakeholder / newcomer walkthrough:** [`docs/milestones/M7/demo-script.md`](docs/milestones/M7/demo-script.md)  
**Sample Business Requirement:** [`docs/milestones/M7/sample-business-requirement.md`](docs/milestones/M7/sample-business-requirement.md)  
**§14.1 DoD checklist:** [`docs/milestones/M7/dod-checklist.md`](docs/milestones/M7/dod-checklist.md)

Additional APIs: `GET /runs/{id}/artefacts`, `GET /runs/{id}/events`, `GET /runs/{id}/lineage`, `POST /runs/{id}/export`, `GET /config/profile`.

### 5. Health endpoints

```bash
curl -s http://127.0.0.1:8000/health | python3 -m json.tool
curl -s http://127.0.0.1:8000/ready | python3 -m json.tool
```

- `GET /health` — process liveness (always 200 if the app is up)  
- `GET /ready` — PostgreSQL readiness (`200` ready / `503` unavailable)

### 6. Production run / HITL APIs

```bash
# Create a run — persists BR, generates Technical Requirement, pauses for TR review
curl -s -X POST http://127.0.0.1:8000/runs -H 'content-type: application/json' \
  -d '{
    "title":"demo",
    "created_by":"consultant",
    "user_context":{"user_id":"consultant"},
    "business_requirement":{
      "title":"Sales analytics data product",
      "intent":"Governed sales analytics data product",
      "objectives":["Analyse order amounts by customer and region"],
      "constraints":["Do not use inaccessible HR datasets"],
      "success_criteria":["All seven artefacts approved via Review Package"]
    }
  }' | python3 -m json.tool

# Inspect run (status, pending_review, latest_artefact)
curl -s http://127.0.0.1:8000/runs/<run_id> | python3 -m json.tool

# Approve each HITL gate in order:
#   technical_requirement → data_model (mapping) → semantic_model
#   → metric_definitions (implementation) → review_package → approved
curl -s -X POST http://127.0.0.1:8000/runs/<run_id>/reviews \
  -H 'content-type: application/json' \
  -d '{"decision":"approve","comments":"ok","reviewer_id":"consultant"}' | python3 -m json.tool

# Audit + lineage
curl -s http://127.0.0.1:8000/runs/<run_id>/events | python3 -m json.tool
curl -s http://127.0.0.1:8000/runs/<run_id>/lineage | python3 -m json.tool

# Optional Databricks export stub (requires approved Review Package; no live deploy)
curl -s -X POST http://127.0.0.1:8000/runs/<run_id>/export \
  -H 'content-type: application/json' \
  -d '{"workspace_label":"mvp-demo-export","catalog":"main","schema":"sales_dp"}' \
  | python3 -m json.tool
```

| Decision | Effect |
| --- | --- |
| `approve` | Advance to next stage (final Review Package approve → `approved` + RP `decision_state=approved`) |
| `reject` | Run status → `terminated` |
| `request_revisions` | Regenerate current stage artefact + return to `waiting_for_review` (metrics revisions regenerate Metric Definitions only) |

### 7. Dev persistence APIs (M1)

```bash
# Create a run row only (no graph) — useful for store/audit validation
curl -s -X POST http://127.0.0.1:8000/dev/runs -H 'content-type: application/json' \
  -d '{"title":"demo"}' | python3 -m json.tool
```

Routes: `POST/GET /dev/runs`, `POST/GET /dev/artefacts`, `POST/GET /dev/lineage`, `GET /dev/audit`.

### 8. Tests and quality

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

### 9. Full stack via Docker Compose

```bash
docker compose up --build
```

API: http://localhost:8000/health

### 10. Pre-commit (optional local hooks)

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
| **M2** | LangGraph + HITL skeleton — **complete** |
| **M3** | Requirements + mapping — **complete** |
| **M4** | Modelling, implementation path, Review Package — **complete** |
| **M5** | Lightweight UI + observability — **complete** |
| **M6** | Adapter boundary + Databricks export stub | **Complete** — [`docs/milestones/M6/`](docs/milestones/M6/) |
| **M7** | MVP demo + DoD | **Complete** — [`docs/milestones/M7/`](docs/milestones/M7/) |

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
| [`docs/milestones/M2/`](docs/milestones/M2/) | M2 close-out evidence |
| [`docs/milestones/M3/`](docs/milestones/M3/) | M3 close-out evidence |
| [`docs/milestones/M4/`](docs/milestones/M4/) | M4 close-out evidence |
| [`docs/milestones/M5/`](docs/milestones/M5/) | M5 close-out evidence |
| [`docs/milestones/M6/`](docs/milestones/M6/) | M6 close-out evidence |
| [`docs/milestones/M7/`](docs/milestones/M7/) | M7 MVP demo + §14.1 DoD |
| [`adr/`](adr/) | Decision records |

---

## License

See [`LICENSE`](LICENSE) (placeholder until SPDX license is confirmed).
