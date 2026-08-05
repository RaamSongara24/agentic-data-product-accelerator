# M2 validation report

## Commands run

```bash
uv sync --group dev
make db && make migrate
make verify
```

## Results

| Check | Result |
| --- | --- |
| `ruff check` / `ruff format --check` | Pass |
| `mypy src` | Pass (strict) |
| Unit tests | 29 passed |
| Integration tests (`-m integration`) | 12 passed (includes M1 persistence + M2 HITL) |

## Acceptance criteria

| # | Criterion | Evidence |
| --- | --- | --- |
| 1 | Creating a run reaches `waiting_for_review` with a stub artefact | `test_create_run_reaches_waiting_for_review` |
| 2 | Approve completes the M2 path | `test_approve_completes_run` → status `approved` |
| 3 | Reject leaves run `terminated` | `test_reject_terminates_run` |
| 4 | Request revisions bumps version, stores feedback, returns to interrupt | `test_request_revisions_bumps_version_and_returns_to_interrupt` |
| 5 | Durability across API process restart | `test_hitl_survives_api_process_restart` (new app lifespan, same Postgres) |
| 6 | Tests cover all three decisions + restart | See integration module above |
| 7 | `make verify` green | This report |
| 8 | Evidence under `docs/milestones/M2/`; README updated | This folder + root README |
| 9 | Commits free of AI-tool branding | Reviewed in close-out |
| 10 | Completion report; local merge; no M3 | Close-out |

## Manual smoke (optional)

```bash
curl -s -X POST http://127.0.0.1:8000/runs -H 'content-type: application/json' \
  -d '{"title":"manual"}' | python3 -m json.tool
# copy run_id, then:
curl -s -X POST http://127.0.0.1:8000/runs/<run_id>/reviews \
  -H 'content-type: application/json' \
  -d '{"decision":"approve","comments":"ok"}' | python3 -m json.tool
```
