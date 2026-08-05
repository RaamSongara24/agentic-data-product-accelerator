# M6 — Validation report

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
| Integration tests (`-m integration`) | 18 passed |

## Acceptance criteria

| # | Criterion | Evidence |
| --- | --- | --- |
| 1 | Adapter interface clear; Databricks stub implements it | `adapters/base.py`, `adapters/databricks/adapter.py` |
| 2 | Export derived from approved canonical artefacts only | Approval gate + `test_export_rejects_unapproved_review_package` |
| 3 | Unit tests pass on frozen fixtures | `tests/unit/fixtures/approved_artefacts.json`, `test_platform_adapter.py` |
| 4 | Discovery without user context fails closed | `test_discovery_without_user_context_fails_closed` |
| 5 | Two concurrent runs with separate threads pass smoke | `tests/integration/test_concurrent_runs.py` |
| 6 | Security checklist + eval set checked in | [`security-checklist.md`](security-checklist.md), [`eval/golden-requirements.md`](eval/golden-requirements.md) |
| 7 | `make verify` green; evidence; local merge | This folder + README |
| 8 | Commits prefixed `M6:` without AI-tool branding | `git log` |

## Exit criterion

Architecture non-goals respected; Databricks adapter ready for future live deploy work (export stub only today).
