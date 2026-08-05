# PRODUCT_SPEC §14.1 — MVP definition of done checklist

Evidence date: **2026-08-05**. Failures are escalated explicitly (not papered over).

| # | Criterion | Result | Evidence |
| --- | --- | --- | --- |
| 1 | **End-to-end path:** BR → Requirements → Mapping (capped judge) → HITL → Modelling → HITL → Implementation → all seven artefacts → Review Package | **Pass** | `test_approve_all_produces_seven_artefacts`; [`demo-script.md`](demo-script.md) |
| 2 | **Must Have coverage:** U1–U4, A1, A3, A4, D1–D4, G1–G4, P1–P3 via thin UI and API | **Pass** | [`must-have-coverage.md`](must-have-coverage.md) |
| 3 | **HITL gates:** review before progression; Approve / Reject / Request revisions; durable Postgres checkpointer | **Pass** | HITL integration tests; ADR 005; M2–M4 evidence |
| 4 | **Lightweight UI:** submit BR, progress, review artefacts, record decisions | **Pass** | `/ui/`; M5 + M7 UI sections |
| 5 | **Governance:** audit + lineage in PostgreSQL; approval state visible before publish | **Pass** | `GET /runs/{id}/events`, `GET /runs/{id}/lineage`; RP `decision_state` |
| 6 | **Persistence:** PG for app data, artefacts, metadata, audit, lineage, checkpoints; storage abstraction | **Pass** | ArtefactStore; migrations; checkpointer |
| 7 | **Source security:** user permissions; inaccessible objects not exposed; governance metadata propagated | **Pass** (fixture-first) | M6 security checklist; fail-closed discovery; residual: no live UC connector — see limitations |
| 8 | **Architecture:** agents write canonical only; adapter boundary (Databricks first); no app RBAC required | **Pass** | Adapters package; `POST /runs/{id}/export` stub; PRODUCT_SPEC §4.3 |
| 9 | **Platform ops:** runtime/config profile; run status + agent decision traces | **Pass** | `GET /config/profile`; events / UI |
| 10 | **Engineering readiness:** uv, FastAPI, LangGraph + PG checkpointer, tests for routing / review transitions | **Pass** | `make verify` — 68 unit + 19 integration |
| 11 | **Documentation:** PRODUCT_SPEC consistent with delivered behaviour | **Pass** | Spec unchanged; delivered behaviour matches §14.1; README/M7 docs updated |

## Residual gaps (orchestrator-owned, non-blocking for §14.1)

| Gap | Notes |
| --- | --- |
| Live Unity Catalog / source connectors | Fixture discovery with ACL semantics; live passthrough is post-MVP |
| Live Databricks deploy | Explicitly out of MVP; export stub only |
| Application RBAC / Business User portal / workflow designer | Explicit non-goals |
| Richer NL UX (U2 optimisation) | Supported via structured fields + optional free text; not NL-first |

## Verdict

**MVP §14.1 definition of done is satisfied** for the September 2026 consultant-led design MVP, with residual platform connectors/deploy owned as post-MVP work.
