# Milestone M6 — Adapter boundary and hardening

| Field | Value |
| --- | --- |
| **Status** | **Complete** |
| **Exit criterion** | Architecture non-goals respected; adapter ready for future live deploy work |
| **Evidence date** | 2026-08-05 |

## Documents

| File | Purpose |
| --- | --- |
| [`implementation-summary.md`](implementation-summary.md) | What was delivered |
| [`validation-report.md`](validation-report.md) | How it was verified |
| [`decisions.md`](decisions.md) | M6 decisions |
| [`known-limitations.md`](known-limitations.md) | Explicit gaps / next milestone boundaries |
| [`architectural-notes.md`](architectural-notes.md) | How M6 fits the architecture |
| [`security-checklist.md`](security-checklist.md) | Discovery ACL + governance propagation checks |
| [`eval/golden-requirements.md`](eval/golden-requirements.md) | Basic eval set (golden Business Requirements) |

## Commands

```bash
uv sync --group dev
make db && make migrate
make verify
```
