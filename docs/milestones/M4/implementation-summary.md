# M4 — Implementation summary

Full seven-artefact canonical path with per-stage HITL, extending the M3 requirements + mapping graph without forking architecture.

## Delivered

| Area | Location |
| --- | --- |
| Modelling Agent | `agents/modelling.py` — Semantic Model + Data Model (Kimball-oriented; deterministic + LLM fallback) |
| Engineer Agent | `agents/engineer.py` — Pipeline Specification |
| Pipeline static validation | `agents/pipeline_validation.py` — stage identity, deps, cycles, structural checks |
| Metrics Agent | `agents/metrics.py` — Metric Definitions |
| Review Package assembly | `agents/review_package.py` — pins artefacts, assumptions, traceability, validation, Qs, recs |
| Implementation path nodes | `orchestration/implementation/` — pipeline → validate → metrics |
| Extended graph | `orchestration/graph.py` — mapping approve → modelling → impl → RP → approved |
| Runner | `orchestration/runner.py` — syncs all five HITL interrupt nodes |

## HITL semantics (ADR 005)

| Gate | Pending artefact | Approve | Reject | Request revisions |
| --- | --- | --- | --- | --- |
| TR | Technical Requirement | Mapping subgraph | Terminate | Regenerate TR |
| Mapping | Data Model (slice) | Modelling | Terminate | Re-run mapping |
| Modelling | Semantic Model | Implementation path | Terminate | Re-run modelling (SM + DM) |
| Implementation | Metric Definitions | Assemble Review Package | Terminate | Regenerate **metrics only** |
| Review Package | Review Package | Run `approved` | Terminate | Reassemble package |

Business Requirement remains consultant intake (persisted, no BR HITL).

## Out of scope (unchanged)

- Lightweight UI (M5)
- PlatformAdapter / Databricks export (M6)
- Live deploy / demo polish beyond tests
