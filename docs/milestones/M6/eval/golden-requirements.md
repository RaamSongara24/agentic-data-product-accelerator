# M6 eval set — golden Business Requirements

Three golden intake requirements used for deterministic agent paths, adapter fixtures, and concurrent-run smoke.

## GR-1 — Sales analytics data product

Used by HITL integration tests and frozen adapter fixtures.

```json
{
  "title": "Sales analytics data product",
  "intent": "Deliver a governed sales analytics data product covering orders, customers, and products for consultant-led design.",
  "objectives": [
    "Analyse order amounts and order counts by customer and region",
    "Support product-level sales reporting"
  ],
  "constraints": [
    "Must not use HR or security datasets the consultant cannot access",
    "Outputs must remain technology-agnostic canonical artefacts"
  ],
  "success_criteria": [
    "Technical Requirement approved via HITL",
    "Mapping data-model slice approved via HITL",
    "All seven canonical artefacts approved via Review Package"
  ],
  "stakeholders": ["data_consultant"]
}
```

## GR-2 — Customer retention analytics

Second concurrent-run smoke input (separate checkpointer `thread_id`).

```json
{
  "title": "Customer retention analytics",
  "intent": "Design a governed customer retention analytics product using only accessible sales and customer datasets.",
  "objectives": [
    "Track repeat order rates by customer segment and region",
    "Support churn risk reporting for sales consultants"
  ],
  "constraints": [
    "Must not use HR payroll or security audit datasets",
    "Canonical artefacts only — no vendor DSL in agent outputs"
  ],
  "success_criteria": [
    "Approved Technical Requirement and mapping slice",
    "Approved Review Package covering seven artefacts"
  ],
  "stakeholders": ["data_consultant", "sales_ops"]
}
```

## GR-3 — Product margin overview (eval-only)

Third golden for offline adapter / agent regression without expanding HITL semantics.

```json
{
  "title": "Product margin overview",
  "intent": "Produce a governed product-margin analytics design from accessible sales and product catalogue sources.",
  "objectives": [
    "Explain margin by product category and region",
    "Support consultant review of measure definitions before platform export"
  ],
  "constraints": [
    "No elevated discovery; inaccessible objects must remain invisible",
    "Platform-specific assets only after Review Package approval"
  ],
  "success_criteria": [
    "Seven canonical artefacts available for review",
    "Optional Databricks export stub derived from approved artefacts only"
  ],
  "stakeholders": ["data_consultant", "finance_analyst"]
}
```

## Usage

| Consumer | Golden |
| --- | --- |
| `tests/integration/test_hitl_api.py` | GR-1 |
| `tests/integration/test_concurrent_runs.py` | GR-1 + GR-2 |
| `tests/unit/fixtures/approved_artefacts.json` | Derived from GR-1 via deterministic agents |
| Future offline eval harness | GR-1 … GR-3 |
