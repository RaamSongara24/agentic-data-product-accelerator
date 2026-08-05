# M5 — Implementation summary

Lightweight consultant review UI and operator observability over the existing M4 `/runs` APIs — no mock bypass of the graph.

## Delivered

| Area | Location |
| --- | --- |
| Static review UI | `ui/static/` — submit BR, progress, artefact viewer, Approve/Reject/Request revisions, events |
| UI mount | `app/main.py` — `/ui/` StaticFiles + `/` → `/ui/` |
| Artefact read APIs | `GET /runs/{id}/artefacts`, `GET /runs/{id}/artefacts/{artefact_id}`, `GET /artefacts/{id}` |
| Operator events | `GET /runs/{id}/events` — audit trail (P2/P3 baseline) |
| Runtime config profile | `GET /config/profile` — non-secret settings for fixed graph (narrow P1) |
| Runner helpers | `HitlRunner.list_artefacts` / `get_artefact` / `list_events` |

## HITL controls (unchanged semantics)

UI decision buttons call `POST /runs/{id}/reviews` with exactly:

- `approve`
- `reject`
- `request_revisions`

Progress badges reflect domain statuses: `created`, `running`, `waiting_for_review`, `approved`, `terminated`, `failed`.

## Out of scope (unchanged)

- Design-system overhaul / Business User portal
- PlatformAdapter / Databricks (M6)
- Workflow designer / app RBAC
