# M7 — MVP demo script

Audience: a newcomer or stakeholder following the README runbook.  
Duration: ~10–15 minutes. Default LLM: `LLM_PROVIDER=deterministic` (no API key).

## 0. Prerequisites

```bash
cp .env.example .env          # defaults are fine for local demo
uv sync --group dev
make db && make migrate
make run
```

Confirm:

```bash
curl -sf http://127.0.0.1:8000/health | python3 -m json.tool
curl -sf http://127.0.0.1:8000/ready | python3 -m json.tool
curl -sf http://127.0.0.1:8000/config/profile | python3 -m json.tool
```

Open [http://127.0.0.1:8000/ui/](http://127.0.0.1:8000/ui/). Config chip should show `deterministic/...`.

Sample intake fields: [`sample-business-requirement.md`](sample-business-requirement.md) (prefilled in the UI).

---

## 1. Submit Business Requirement (canonical start)

1. Keep or lightly edit the prefilled **Sales analytics data product** form.
2. Click **Start run**.
3. Note `run_id` and status `waiting_for_review`.
4. Stage list highlights **Technical Requirement**.

**Talking point:** the product is a governed path to **seven canonical artefacts**, not Databricks notebooks.

---

## 2. Staged HITL reviews → Review Package

Approve each gate in order (comments optional):

| Order | Artefact under review | After approve |
| --- | --- | --- |
| 1 | Technical Requirement | Mapping Data Model pending |
| 2 | Data Model (mapping) | Semantic Model pending |
| 3 | Semantic Model | Metric Definitions pending (pipeline + metrics generated) |
| 4 | Metric Definitions | Review Package pending |
| 5 | Review Package | Run status **`approved`** |

At each gate, open the artefact JSON viewer and confirm payloads are technology-agnostic (no vendor job DSL as primary content).

### Alternate paths (spot-check once)

- **Reject** at any gate → status `terminated`; decisions disabled.
- **Request revisions** on TR → new TR version; still `waiting_for_review`.

---

## 3. Audit trail

In UI section **5. Operator events**, confirm actions such as:

- `run_created`, `run_status_updated`
- `artefact_created`
- `review_submitted`
- `lineage_created`

Or via API:

```bash
curl -s http://127.0.0.1:8000/runs/<run_id>/events | python3 -m json.tool | head -80
```

---

## 4. Lineage

UI section **6. Lineage** lists `derived_from` edges between artefact versions.

```bash
curl -s http://127.0.0.1:8000/runs/<run_id>/lineage | python3 -m json.tool
```

**Talking point:** lineage and audit live in PostgreSQL; graph state holds refs, not opaque chat history.

---

## 5. Canonical outputs (product identity)

```bash
curl -s http://127.0.0.1:8000/runs/<run_id>/artefacts | python3 -m json.tool
```

Expect all seven types. Load the latest Review Package and confirm `decision_state` is **`approved`** (in-platform publish).

---

## 6. Optional Databricks export (adapter demo)

UI section **7** → **Export stub (Databricks)** after approval.

Or:

```bash
curl -s -X POST http://127.0.0.1:8000/runs/<run_id>/export \
  -H 'content-type: application/json' \
  -d '{"workspace_label":"mvp-demo-export","catalog":"main","schema":"sales_dp"}' \
  | python3 -m json.tool
```

Confirm:

- `mode` = `export_stub`
- warnings state **no live deploy**
- `manifest.json` content has `"deploy": false`

**Talking point:** export is an **optional adapter demonstration**. Canonical artefacts remain the product.

---

## 7. API-only path (optional)

Same flow without the UI — see README § Production run / HITL APIs. Approve five HITL gates after `POST /runs`.

---

## Success criteria for this walkthrough

| Check | Expected |
| --- | --- |
| Submit → staged reviews → approved RP | Status `approved`; seven artefact types present |
| Audit | Events list non-empty with review + artefact actions |
| Lineage | Multiple `derived_from` edges |
| Canonical clarity | Artefacts are technology-agnostic; UI/docs say so |
| Optional export | Stub only; labeled; gated on approved RP |
