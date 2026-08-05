# M6 — Implementation summary

Platform adapter boundary with Databricks export stub and hardening checks, without live deploy.

## Delivered

| Area | Location |
| --- | --- |
| `PlatformAdapter` interface | `adapters/base.py` — `to_platform(artefacts, target_config) -> AdapterResult` |
| Adapter types | `adapters/types.py` — `AdapterTargetConfig`, `AdapterAsset`, `AdapterResult` |
| Databricks stub/export | `adapters/databricks/adapter.py` — YAML/JSON/notebooks-as-files from **approved** artefacts |
| Adapter errors | `adapters/errors.py` |
| Error taxonomy | `observability/errors.py` — stable `ErrorCode` + `AppError` |
| Structured logging | `observability/logging_setup.py` — `log_event` / `log_app_error` + JSON extras |
| Fail-closed discovery | `integrations/discovery/service.py` + mapping subgraph (no default principal) |
| Frozen fixtures | `tests/unit/fixtures/approved_artefacts.json` |
| Security checklist | [`security-checklist.md`](security-checklist.md) |
| Eval set | [`eval/golden-requirements.md`](eval/golden-requirements.md) |

## Export behaviour

- Requires Review Package with `decision_state == "approved"`.
- Exports Pipeline Specification, Data Model, Semantic Model, and Metric Definitions only.
- Propagates `governance_metadata` into manifest and platform-shaped assets.
- `deploy: false` — no jobs, notebooks, or Unity Catalog objects are created in a workspace.

## Hardening

- Discovery without authenticated user context raises `DiscoveryPermissionError` (HTTP 403 via runner mapping).
- Runner no longer invents a `"consultant"` principal when `user_context` is omitted.
- Mapping subgraph fails closed when `user_id` is absent from graph state.

## Out of scope (unchanged)

- Live Databricks deployment / job scheduling
- Fabric / Snowflake / Power BI adapters
- HITL semantic changes or new artefact types
- M7 demo polish
