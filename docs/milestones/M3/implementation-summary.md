# M3 — Implementation summary

Business Requirement → Technical Requirement generation, fixture-first mapping subgraph with Mapping Judge retry caps, dual HITL gates, and user-context discovery filtering — all via the existing `/runs` APIs.

## Delivered

| Area | Location |
| --- | --- |
| Requirements Agent | `agents/requirements.py` — deterministic BR→TR (golden-stable); optional OpenAI-compatible path |
| LLM client plumbing | `integrations/llm/` — `deterministic` default; `openai_compatible` via env (`LLM_*`); secrets never in graph state |
| Discovery fixtures | `integrations/discovery/` — catalogue ACL; inaccessible objects filtered by `UserContext` |
| Mapping subgraph | `orchestration/mapping/` — discovery → data mapping → judge → persist Data Model slice |
| Multi-stage graph | `orchestration/graph.py` — ensure BR → generate TR → HITL → mapping → HITL → approved |
| Runner | `orchestration/runner.py` — syncs `await_tr_review` / `await_mapping_review` interrupts |
| Settings | `config/settings.py` — LLM + mapping retry caps |

## HITL semantics (ADR 005)

| Gate | Artefact | Approve | Reject | Request revisions |
| --- | --- | --- | --- | --- |
| TR | Technical Requirement | Enter mapping subgraph | Terminate | Regenerate TR |
| Mapping | Data Model (mapping slice) | Run `approved` (M3 exit) | Terminate | Re-run mapping subgraph |

Business Requirement is consultant intake (persisted, no BR HITL in M3).

## Out of scope (unchanged)

- Semantic / Pipeline / Metrics / Review Package agents (M4)
- UI (M5), live Unity Catalog connectors, Databricks adapter (M6)
