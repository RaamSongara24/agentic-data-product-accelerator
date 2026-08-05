"""Golden fixture: Business Requirement → Technical Requirement properties."""

from __future__ import annotations

from agentic_data_product.agents.requirements import (
    GOLDEN_REQUIRED_BEHAVIOURS,
    GOLDEN_TR_SUMMARY_PREFIX,
    generate_technical_requirement_deterministic,
)
from agentic_data_product.domain.artefacts import BusinessRequirementPayload

GOLDEN_BR = BusinessRequirementPayload(
    title="Sales analytics data product",
    intent=(
        "Deliver a governed sales analytics data product covering orders, "
        "customers, and products for consultant-led design."
    ),
    objectives=[
        "Analyse order amounts and order counts by customer and region",
        "Support product-level sales reporting",
    ],
    constraints=[
        "Must not use HR or security datasets the consultant cannot access",
        "Outputs must remain technology-agnostic canonical artefacts",
    ],
    success_criteria=[
        "Technical Requirement approved via HITL",
        "Mapping data-model slice approved via HITL",
    ],
    stakeholders=["data_consultant"],
)


def test_golden_br_produces_expected_tr_properties() -> None:
    tr = generate_technical_requirement_deterministic(GOLDEN_BR)

    assert tr.summary.startswith(GOLDEN_TR_SUMMARY_PREFIX)
    assert "Sales analytics" in tr.summary
    for behaviour in GOLDEN_REQUIRED_BEHAVIOURS:
        assert behaviour in tr.behaviours

    assert "Order" in tr.entities
    assert "Customer" in tr.entities
    assert "Product" in tr.entities

    assert any(f.startswith("fact_") for f in tr.candidate_facts)
    assert "Date" in tr.candidate_dimensions
    assert "Customer" in tr.candidate_dimensions or "customer" in [
        d.lower() for d in tr.candidate_dimensions
    ]
    assert "order_amount" in tr.candidate_measures or "order_count" in tr.candidate_measures

    assert tr.governance_requirements == list(GOLDEN_BR.constraints)
    assert tr.acceptance_criteria == list(GOLDEN_BR.success_criteria)
    assert tr.transformations  # non-empty mappings guidance


def test_golden_tr_incorporates_revision_feedback() -> None:
    tr = generate_technical_requirement_deterministic(
        GOLDEN_BR,
        feedback="Add explicit grain for order_amount",
    )
    assert any("Add explicit grain" in b for b in tr.behaviours)
