# M5 — Manual happy-path script

Goal: complete an approve-all consultant demo **without** raw API clients.

## Prerequisites

```bash
uv sync --group dev
make db && make migrate
make run
```

Open [http://127.0.0.1:8000/ui/](http://127.0.0.1:8000/ui/). Confirm the config chip shows the active profile (for example `deterministic/...`).

## Steps

1. **Submit Business Requirement** — keep or edit the prefilled sales analytics fields; click **Start run**.
2. **Progress** — status becomes `waiting_for_review`; Technical Requirement is highlighted.
3. **Artefact viewer** — confirm TR payload JSON is visible (or click **Load**).
4. **Approve** TR → mapping Data Model pending → **Approve**.
5. **Approve** Semantic Model → Metric Definitions pending → **Approve**.
6. **Approve** Review Package → status `approved`; all seven stages show versions.
7. **Operator events** — scroll to section 5; confirm `run_created`, `artefact_created`, `review_submitted`, and status updates.

## Alternate paths (spot-check)

- **Reject** at any HITL gate → status `terminated`; decision buttons disabled.
- **Request revisions** on TR → new TR version; still `waiting_for_review`.

## Screenshots

See [`screenshots/`](screenshots/):

| File | State |
| --- | --- |
| `01-submit-business-requirement.png` | Intake form |
| `02-waiting-for-review.png` | HITL + artefact viewer |
| `03-approved-with-events.png` | Approved run + events |
| `04-terminated.png` | Reject / terminated |
