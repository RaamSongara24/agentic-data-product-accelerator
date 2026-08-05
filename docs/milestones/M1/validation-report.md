# M1 validation report

## Environment

- Python 3.12 + `uv`
- PostgreSQL 16 via `docker compose` (`make db`)
- Commands: `uv sync --group dev`, `make migrate`, `make verify`

## Results (2026-08-05)

| Check | Result |
| --- | --- |
| `ruff check` + `ruff format --check` | PASS |
| `mypy src` (strict) | PASS |
| Unit tests (`tests/unit`) | PASS — 22 tests |
| Integration tests (`tests/integration`, Postgres) | PASS — 6 tests |
| **`make verify`** | **PASS** |

## Coverage against acceptance criteria

| Criterion | Evidence |
| --- | --- |
| Seven artefact payloads validate | `test_artefact_schemas.py` (parametrized + per-type cases) |
| Versioned create/get/list; unique `(run, type, version)` | `test_persistence_crud_flow` — v1/v2, conflict → 409, list refs |
| Audit on run/artefact creation | Same flow asserts `run_created` / `artefact_created` (and lineage) |
| Lineage create/list for a run | POST `/dev/lineage`, GET `/dev/lineage?run_id=` |
| Invalid payload → 422 (not 404) | `test_invalid_artefact_payload_returns_422` |
| Missing run → 404 | `test_artefact_for_missing_run_returns_404` |
| No M2+ scope creep | Grep / package layout: no graph, HITL, agents, adapters |

## Optional smoke (manual)

```bash
make db && make migrate && make run
# POST /dev/runs, POST /dev/artefacts, GET /dev/audit?run_id=…, GET /dev/lineage?run_id=…
```
