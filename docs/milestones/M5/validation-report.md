# M5 — Validation report

## Commands

```bash
uv sync --group dev
make db && make migrate
make verify
```

## Results (2026-08-05)

| Check | Result |
| --- | --- |
| `ruff check` / `ruff format --check` | Pass |
| `mypy src` (strict) | Pass |
| Unit tests | 58 passed |
| Integration tests (`-m integration`) | 17 passed |

## Acceptance criteria

| # | Criterion | Evidence |
| --- | --- | --- |
| 1 | Consultant can submit BR in UI and start a run | UI form → `POST /runs`; [`happy-path.md`](happy-path.md); screenshot `01-submit-business-requirement.png` |
| 2 | Progress tracks HITL states | Status badge + stage list; screenshots `02`–`04` |
| 3 | Artefact viewer shows current content | `GET /runs/{id}/artefacts/{id}`; screenshot `02-waiting-for-review.png` |
| 4 | Decision controls hit API | Approve / Reject / Request revisions → `POST /runs/{id}/reviews` |
| 5 | Agent/operator events visible | `GET /runs/{id}/events`; screenshot `03-approved-with-events.png` |
| 6 | Happy-path script + screenshots | [`happy-path.md`](happy-path.md) + [`screenshots/`](screenshots/) |
| 7 | `make verify` green + evidence + local merge | This folder + README |
| 8 | Commits prefixed `M5:` without AI-tool branding | `git log` |

## Exit criterion

Demo can be run without raw API clients (`http://127.0.0.1:8000/ui/`).
