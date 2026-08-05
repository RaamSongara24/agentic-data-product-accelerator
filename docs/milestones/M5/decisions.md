# M5 — Decisions

| ID | Decision | Rationale |
| --- | --- | --- |
| D1 | Static HTML/CSS/JS under `ui/static/` (no SPA build) | Lightweight MVP; serves from FastAPI without a frontend toolchain |
| D2 | Production artefact/event read routes (not `/dev` only) | UI must use production contracts; `/dev` remains store validation |
| D3 | `GET /config/profile` returns non-secret settings only | Narrow P1 for fixed graph; never expose `llm_api_key` |
| D4 | Events = existing audit trail | Sufficient P2/P3 baseline without a new event bus |
| D5 | Exact HITL button set: Approve / Reject / Request revisions | ADR 005 / product spec; no extra workflow semantics |
| D6 | No M6 adapter work in this milestone | Orchestrator gates next work |
