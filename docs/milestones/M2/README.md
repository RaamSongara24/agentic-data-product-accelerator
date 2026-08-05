# Milestone M2 — HITL skeleton

| Field | Value |
| --- | --- |
| **Status** | **Complete** |
| **Exit criterion** | Durable HITL works across API process restart |
| **Evidence date** | 2026-08-05 |

## Documents

| File | Purpose |
| --- | --- |
| [`implementation-summary.md`](implementation-summary.md) | What was delivered |
| [`validation-report.md`](validation-report.md) | How it was verified |
| [`decisions.md`](decisions.md) | M2 decisions |
| [`known-limitations.md`](known-limitations.md) | Explicit gaps / next milestone boundaries |
| [`architectural-notes.md`](architectural-notes.md) | How M2 fits the architecture |

## Commands

```bash
uv sync --group dev
make db && make migrate
make verify
```

## Quick API smoke

```bash
# Start API (Postgres already up + migrated)
uv run uvicorn agentic_data_product.app.main:app --host 0.0.0.0 --port 8000

curl -s -X POST http://127.0.0.1:8000/runs -H 'content-type: application/json' \
  -d '{"title":"demo"}' | python3 -m json.tool
```
