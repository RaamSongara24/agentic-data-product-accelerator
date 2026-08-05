# Milestone M4 — Modelling, implementation path, Review Package

| Field | Value |
| --- | --- |
| **Status** | **Complete** |
| **Exit criterion** | All seven artefacts produced and approvable via API |
| **Evidence date** | 2026-08-05 |

## Documents

| File | Purpose |
| --- | --- |
| [`implementation-summary.md`](implementation-summary.md) | What was delivered |
| [`validation-report.md`](validation-report.md) | How it was verified |
| [`decisions.md`](decisions.md) | M4 decisions |
| [`known-limitations.md`](known-limitations.md) | Explicit gaps / next milestone boundaries |
| [`architectural-notes.md`](architectural-notes.md) | How M4 fits the architecture |

## Commands

```bash
uv sync --group dev
make db && make migrate
make verify
```

## Quick API smoke (approve-all seven artefacts)

```bash
uv run uvicorn agentic_data_product.app.main:app --host 0.0.0.0 --port 8000

# Create run → waiting on Technical Requirement
# Then approve in order:
#   TR → mapping Data Model → Semantic Model → Metric Definitions → Review Package
# Final approve on Review Package → run status approved
```
