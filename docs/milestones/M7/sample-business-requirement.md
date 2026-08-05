# Sample Business Requirement — MVP demo (GR-1)

This is the golden **Sales analytics** intake used by the UI prefills, HITL integration tests, and the stakeholder demo. Source of truth for the eval set: [`../M6/eval/golden-requirements.md`](../M6/eval/golden-requirements.md).

## Structured fields

| Field | Value |
| --- | --- |
| **Title** | Sales analytics data product |
| **Intent** | Deliver a governed sales analytics data product covering orders, customers, and products for consultant-led design. |
| **Objectives** | Analyse order amounts and order counts by customer and region; Support product-level sales reporting |
| **Constraints** | Must not use HR or security datasets the consultant cannot access; Outputs must remain technology-agnostic canonical artefacts |
| **Success criteria** | Technical Requirement approved via HITL; Mapping data-model slice approved via HITL; All seven canonical artefacts approved via Review Package |
| **Stakeholders** | data_consultant |

## JSON (API `business_requirement`)

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

## Notes

- Natural-language elaboration (U2) may accompany structure; MVP UX centres on this structured form.
- Discovery is fixture-first with fail-closed ACL; inaccessible HR/security objects must not appear in artefacts.
