# Milestone M5 — Lightweight UI and observability

| Field | Value |
| --- | --- |
| **Status** | **Complete** |
| **Exit criterion** | Demo can be run without raw API clients |
| **Evidence date** | 2026-08-05 |

## Documents

| File | Purpose |
| --- | --- |
| [`implementation-summary.md`](implementation-summary.md) | What was delivered |
| [`validation-report.md`](validation-report.md) | How it was verified |
| [`decisions.md`](decisions.md) | M5 decisions |
| [`known-limitations.md`](known-limitations.md) | Explicit gaps / next milestone boundaries |
| [`architectural-notes.md`](architectural-notes.md) | How M5 fits the architecture |
| [`happy-path.md`](happy-path.md) | Manual consultant happy-path script |
| [`screenshots/`](screenshots/) | Key UI states |

## Commands

```bash
uv sync --group dev
make db && make migrate
make verify
make run
# Open http://127.0.0.1:8000/ui/
```
