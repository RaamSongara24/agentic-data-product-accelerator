# M6 — Decisions

| ID | Decision | Rationale |
| --- | --- | --- |
| D1 | `PlatformAdapter.to_platform` matches ARCHITECTURE §11 | Keep ADR 004 contract stable for future adapters |
| D2 | Databricks adapter is export/stub only (`mode=export_stub`) | MVP does not require live deploy; stub proves mapping |
| D3 | Approval gate = Review Package `decision_state == "approved"` | Adapters consume approved canonical artefacts only |
| D4 | Discovery fails closed when user context is missing | Security: never invent a default principal or return full catalogue |
| D5 | Central `ErrorCode` / `AppError` taxonomy | Structured logs + consistent HTTP mapping without ad-hoc strings |
| D6 | Minimal YAML emitter (no PyYAML dependency) | Keep stub export lightweight; JSON remains primary fixture format |
| D7 | No M7 demo work in this milestone | Orchestrator gates next work |
