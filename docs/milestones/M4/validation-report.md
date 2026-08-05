# M4 — Validation report

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
| Unit tests | 55 passed |
| Integration tests (`-m integration`) | 15 passed |

## Acceptance criteria

| # | Criterion | Evidence |
| --- | --- | --- |
| 1 | Approve-all path produces all seven artefacts via API | `test_approve_all_produces_seven_artefacts` |
| 2 | Reject at mid-stage terminates | `test_reject_mid_stage_modelling_terminates` (+ TR/mapping reject tests) |
| 3 | Request revisions on Metric Definitions regenerates only that stage | `test_request_revisions_on_metrics_only_regenerates_metrics` |
| 4 | Pipeline Spec static validation feeds Review Package | Same approve-all test asserts `validation_results` on RP |
| 5 | Audit + lineage coherent across stages | Store `save_artefact` + `create_lineage_edge` per stage; persistence tests |
| 6 | `make verify` green + evidence + local merge | This folder + README |
| 7 | Commits prefixed `M4:` without AI-tool branding | `git log` |

## Exit criterion

All seven artefacts produced and approvable via API; Review Package approve → `approved`.
