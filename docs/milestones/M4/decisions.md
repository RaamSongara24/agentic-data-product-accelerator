# M4 — Decisions

| ID | Decision | Rationale |
| --- | --- | --- |
| D1 | Mapping approve enters modelling (not terminal `approved`) | M4 exit is Review Package; M3 exit was mapping |
| D2 | Modelling HITL pending artefact = Semantic Model | Both SM + DM persisted; one interrupt pointer; revisions re-run modelling |
| D3 | Modelling continues the mapping Data Model artefact id | Version continuity for the same logical Data Model |
| D4 | Implementation HITL pending = Metric Definitions | AC requires revisions regenerate metrics only |
| D5 | Pipeline Spec generated + validated before metrics; not separately HITL'd | Deliverable “HITL at modelling, implementation, and Review Package”; validation still feeds RP |
| D6 | Deterministic heuristics for agents under `LLM_PROVIDER=deterministic` | Golden/integration stability; mirrors M3 Requirements Agent pattern |
| D7 | No M5 UI / M6 adapter in this milestone | Scope control; orchestrator gates next work |
