# M7 — Validation report

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
| Unit tests | 68 passed |
| Integration tests (`-m integration`) | 19 passed |

## Acceptance criteria

| # | Criterion | Evidence |
| --- | --- | --- |
| 1 | Demo script runnable via README | [`demo-script.md`](demo-script.md), README Quick start |
| 2 | Walkthrough: staged HITL → approved RP | Demo script §2; HITL + M7 integration tests |
| 3 | Audit and lineage demonstrable | `/events`, `/lineage`, UI sections 5–6 |
| 4 | Canonical identity clear; export optional & labeled | UI §7; export `mode=export_stub`; demo script §5–6 |
| 5 | §14.1 checklist with pass/fail | [`dod-checklist.md`](dod-checklist.md) |
| 6 | Evidence under `docs/milestones/M7/`; completion report; local merge | This folder + completion report |
| 7 | Commits prefixed `M7:` without AI-tool branding | `git log` |

## Exit criterion

PRODUCT_SPEC §14.1 satisfied; residual connectors/deploy listed in [`known-limitations.md`](known-limitations.md) for orchestrator ownership.
