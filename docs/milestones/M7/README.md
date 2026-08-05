# Milestone M7 — MVP demonstration and definition of done

| Field | Value |
| --- | --- |
| **Status** | **Complete** |
| **Exit criterion** | PRODUCT_SPEC §14.1 MVP definition of done satisfied (residual gaps owned below) |
| **Evidence date** | 2026-08-05 |

## Documents

| File | Purpose |
| --- | --- |
| [`demo-script.md`](demo-script.md) | Stakeholder / newcomer walkthrough |
| [`sample-business-requirement.md`](sample-business-requirement.md) | Sample Business Requirement (GR-1) |
| [`dod-checklist.md`](dod-checklist.md) | PRODUCT_SPEC §14.1 item-by-item pass/fail |
| [`must-have-coverage.md`](must-have-coverage.md) | Must Have story coverage map |
| [`implementation-summary.md`](implementation-summary.md) | What M7 delivered |
| [`validation-report.md`](validation-report.md) | How it was verified |
| [`decisions.md`](decisions.md) | M7 decisions |
| [`known-limitations.md`](known-limitations.md) | Residual gaps / orchestrator ownership |
| [`architectural-notes.md`](architectural-notes.md) | How demo polish fits the architecture |
| [`completion-report.md`](completion-report.md) | Milestone completion report |

## Commands

```bash
uv sync --group dev
cp .env.example .env   # if needed
make db && make migrate
make verify
make run
```

Open [http://127.0.0.1:8000/ui/](http://127.0.0.1:8000/ui/) and follow [`demo-script.md`](demo-script.md).
