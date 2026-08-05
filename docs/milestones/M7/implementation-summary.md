# M7 — Implementation summary

MVP demonstration packaging and small polish so a newcomer can run the consultant happy path and close PRODUCT_SPEC §14.1.

## Delivered

| Area | Change |
| --- | --- |
| Review Package publish | On final Approve, persist new RP version with `decision_state=approved` (in-platform publish) |
| Production lineage API | `GET /runs/{run_id}/lineage` |
| Optional export API | `POST /runs/{run_id}/export` — Databricks **export stub** only; gated on approved RP |
| Consultant UI | Sections for lineage + optional export (labeled non-deploy) |
| Demo materials | Demo script, sample BR, §14.1 checklist, must-have map |
| README runbook | Env vars, M7 status, lineage/export commands, demo pointer |
| Tests | `tests/integration/test_m7_demo_apis.py`; HITL approve-all asserts RP approved |

## Out of scope (unchanged)

- Live Databricks deploy
- Live source connectors / Unity Catalog
- Application RBAC, Business User portal, workflow designer
- New major agent/feature work beyond demo polish
