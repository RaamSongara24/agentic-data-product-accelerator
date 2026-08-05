# Milestone M3 — Requirements and mapping

| Field | Value |
| --- | --- |
| **Status** | **Complete** |
| **Exit criterion** | Consultant (API) can approve through mapping stage |
| **Evidence date** | 2026-08-05 |

## Documents

| File | Purpose |
| --- | --- |
| [`implementation-summary.md`](implementation-summary.md) | What was delivered |
| [`validation-report.md`](validation-report.md) | How it was verified |
| [`decisions.md`](decisions.md) | M3 decisions |
| [`known-limitations.md`](known-limitations.md) | Explicit gaps / next milestone boundaries |
| [`architectural-notes.md`](architectural-notes.md) | How M3 fits the architecture |

## Commands

```bash
uv sync --group dev
make db && make migrate
make verify
```

## Quick API smoke (approve through mapping)

```bash
uv run uvicorn agentic_data_product.app.main:app --host 0.0.0.0 --port 8000

# Create run with Business Requirement + user context
curl -s -X POST http://127.0.0.1:8000/runs -H 'content-type: application/json' \
  -d '{
    "title":"sales dp",
    "created_by":"consultant",
    "user_context":{"user_id":"consultant"},
    "business_requirement":{
      "title":"Sales analytics",
      "intent":"Governed sales analytics",
      "objectives":["Analyse order amounts by customer"],
      "constraints":["No inaccessible HR data"],
      "success_criteria":["TR and mapping approved"]
    }
  }' | python3 -m json.tool

# Approve Technical Requirement, then approve mapping data-model slice
curl -s -X POST http://127.0.0.1:8000/runs/<run_id>/reviews \
  -H 'content-type: application/json' \
  -d '{"decision":"approve","reviewer_id":"consultant"}' | python3 -m json.tool
```
