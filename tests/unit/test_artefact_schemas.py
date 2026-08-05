"""Unit tests for the seven canonical artefact payload schemas."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from agentic_data_product.domain import (
    ArtefactRef,
    ArtefactType,
    BusinessRequirementPayload,
    DataModelPayload,
    MetricDefinitionsPayload,
    PipelineSpecificationPayload,
    ReviewPackagePayload,
    SemanticModelPayload,
    TechnicalRequirementPayload,
    validate_artefact_payload,
)


def test_business_requirement_valid() -> None:
    model = BusinessRequirementPayload.model_validate(
        {
            "title": "Sales analytics",
            "intent": "Understand regional sales performance",
            "objectives": ["Track revenue by region"],
            "constraints": ["PII excluded"],
            "success_criteria": ["Dashboard within 5s"],
        }
    )
    assert model.title == "Sales analytics"


def test_business_requirement_requires_objectives() -> None:
    with pytest.raises(ValidationError):
        BusinessRequirementPayload.model_validate(
            {
                "title": "x",
                "intent": "y",
                "objectives": [],
            }
        )


def test_technical_requirement_valid() -> None:
    model = TechnicalRequirementPayload.model_validate(
        {
            "summary": "Regional sales mart",
            "behaviours": ["Aggregate daily orders"],
            "entities": ["Order", "Region"],
            "acceptance_criteria": ["Matches finance totals"],
        }
    )
    assert "Order" in model.entities


def test_semantic_model_valid() -> None:
    model = SemanticModelPayload.model_validate(
        {
            "name": "Sales semantic",
            "description": "Business view of sales",
            "metrics": [{"name": "revenue", "definition": "SUM(amount)"}],
            "dimensions": [{"name": "region", "definition": "Sales region"}],
        }
    )
    assert model.metrics[0].name == "revenue"


def test_data_model_valid() -> None:
    model = DataModelPayload.model_validate(
        {
            "name": "Sales DM",
            "description": "Star schema",
            "entities": [
                {
                    "name": "fact_sales",
                    "attributes": [
                        {"name": "amount", "data_type": "decimal", "nullable": False},
                    ],
                    "primary_key": ["order_id"],
                }
            ],
        }
    )
    assert model.entities[0].name == "fact_sales"


def test_data_model_requires_entity() -> None:
    with pytest.raises(ValidationError):
        DataModelPayload.model_validate({"name": "x", "description": "y", "entities": []})


def test_pipeline_specification_valid() -> None:
    model = PipelineSpecificationPayload.model_validate(
        {
            "name": "Sales pipeline",
            "description": "Daily load",
            "stages": [
                {
                    "name": "ingest_orders",
                    "kind": "ingest",
                    "description": "Load orders",
                    "outputs": ["orders_raw"],
                }
            ],
        }
    )
    assert model.stages[0].kind == "ingest"


def test_metric_definitions_valid() -> None:
    model = MetricDefinitionsPayload.model_validate(
        {
            "name": "Sales KPIs",
            "description": "Core KPIs",
            "metrics": [
                {
                    "name": "revenue",
                    "description": "Total revenue",
                    "calculation": "SUM(amount)",
                    "aggregation": "sum",
                    "grain": "day,region",
                }
            ],
        }
    )
    assert model.metrics[0].grain == "day,region"


def test_review_package_valid() -> None:
    ref = ArtefactRef(
        artefact_id=uuid4(),
        artefact_type=ArtefactType.BUSINESS_REQUIREMENT,
        version=1,
        run_id=uuid4(),
    )
    model = ReviewPackagePayload.model_validate(
        {
            "title": "Review pack",
            "summary": "Ready for review",
            "pinned_artefacts": [ref.model_dump(mode="json")],
            "assumptions": ["Source data daily"],
        }
    )
    assert model.decision_state == "draft"


@pytest.mark.parametrize(
    ("artefact_type", "payload"),
    [
        (
            ArtefactType.BUSINESS_REQUIREMENT,
            {
                "title": "t",
                "intent": "i",
                "objectives": ["o"],
            },
        ),
        (
            ArtefactType.TECHNICAL_REQUIREMENT,
            {"summary": "s", "behaviours": ["b"]},
        ),
        (
            ArtefactType.SEMANTIC_MODEL,
            {"name": "n", "description": "d"},
        ),
        (
            ArtefactType.DATA_MODEL,
            {
                "name": "n",
                "description": "d",
                "entities": [{"name": "e", "attributes": []}],
            },
        ),
        (
            ArtefactType.PIPELINE_SPECIFICATION,
            {
                "name": "n",
                "description": "d",
                "stages": [{"name": "s", "description": "x"}],
            },
        ),
        (
            ArtefactType.METRIC_DEFINITIONS,
            {
                "name": "n",
                "description": "d",
                "metrics": [
                    {
                        "name": "m",
                        "description": "d",
                        "calculation": "c",
                        "aggregation": "sum",
                        "grain": "day",
                    }
                ],
            },
        ),
        (
            ArtefactType.REVIEW_PACKAGE,
            {
                "title": "t",
                "summary": "s",
                "pinned_artefacts": [
                    {
                        "artefact_id": str(uuid4()),
                        "artefact_type": "business_requirement",
                        "version": 1,
                        "run_id": str(uuid4()),
                    }
                ],
            },
        ),
    ],
)
def test_validate_artefact_payload_all_types(
    artefact_type: ArtefactType,
    payload: dict[str, object],
) -> None:
    validated = validate_artefact_payload(artefact_type, payload)
    assert validated.model_dump()


def test_validate_artefact_payload_rejects_invalid() -> None:
    with pytest.raises(ValidationError):
        validate_artefact_payload(
            ArtefactType.BUSINESS_REQUIREMENT,
            {"title": "only"},
        )


def test_all_seven_artefact_types_registered() -> None:
    assert len(ArtefactType) == 7
