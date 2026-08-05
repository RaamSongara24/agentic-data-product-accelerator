# M3 — Validation report

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
| Unit tests | 41 passed |
| Integration tests (`-m integration`) | 13 passed |

## Acceptance criteria

| # | Criterion | Evidence |
| --- | --- | --- |
| 1 | Submit BR → obtain TR for review | `test_create_run_reaches_tr_waiting_for_review` |
| 2 | Approve / Reject / Request revisions at TR HITL | Integration HITL tests |
| 3 | Fixture-first discovery with user-context filtering | `test_discovery_acl` + mapping integration |
| 4 | Judge retry caps and escalation | `test_mapping_judge` |
| 5 | Inaccessible fixtures never in outputs | ACL unit tests + `test_approve_through_mapping_stage` payload scan |
| 6 | Approve through mapping stage (API) | `test_approve_through_mapping_stage` |
| 7 | `make verify` green + evidence | This folder + README |
| 8 | Commits prefixed `M3:` without AI-tool branding | `git log` |

## Exit criterion

Consultant can approve Technical Requirement then mapping Data Model slice via API; run reaches `approved`.
