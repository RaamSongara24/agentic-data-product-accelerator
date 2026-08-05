"""Unit tests for modelling / engineer / metrics / pipeline validation agents."""

from __future__ import annotations

from uuid import UUID

import pytest

from agentic_data_product.agents.engineer import generate_pipeline_specification_deterministic
from agentic_data_product.agents.metrics import generate_metric_definitions_deterministic
from agentic_data_product.agents.modelling import (
    GOLDEN_SEMANTIC_NAME_PREFIX,
    generate_modelling_deterministic,
)
from agentic_data_product.agents.pipeline_validation import validate_pipeline_specification
from agentic_data_product.agents.requirements import generate_technical_requirement_deterministic
from agentic_data_product.agents.review_package import assemble_review_package
from agentic_data_product.domain.artefacts import (
    ArtefactRef,
    BusinessRequirementPayload,
    PipelineSpecificationPayload,
    PipelineStage,
)
from agentic_data_product.domain.enums import ArtefactType


@pytest.fixture
def tr_payload():
    br = BusinessRequirementPayload(
        title="Sales analytics data product",
        intent="Governed sales analytics",
        objectives=["Analyse order amounts by customer and region"],
        constraints=["No inaccessible datasets"],
        success_criteria=["Approved Review Package"],
    )
    return generate_technical_requirement_deterministic(br)


def test_modelling_deterministic_produces_semantic_and_data_model(tr_payload) -> None:
    semantic, data_model = generate_modelling_deterministic(tr_payload)
    assert semantic.name.startswith(GOLDEN_SEMANTIC_NAME_PREFIX)
    assert semantic.metrics
    assert semantic.dimensions
    assert any(e.name == "FactOrder" for e in data_model.entities)


def test_modelling_incorporates_feedback(tr_payload) -> None:
    semantic, data_model = generate_modelling_deterministic(
        tr_payload,
        feedback="Add clearer grain notes",
    )
    assert "reviewer_feedback" in semantic.business_definitions
    assert data_model.mapping_context.get("modelling_feedback")


def test_pipeline_and_metrics_deterministic(tr_payload) -> None:
    semantic, data_model = generate_modelling_deterministic(tr_payload)
    pipeline = generate_pipeline_specification_deterministic(
        tr=tr_payload,
        semantic=semantic,
        data_model=data_model,
    )
    assert pipeline.stages
    results = validate_pipeline_specification(pipeline)
    assert any(r.startswith("PASS:") for r in results)
    assert not any(r.startswith("FAIL:") for r in results)

    metrics = generate_metric_definitions_deterministic(
        semantic=semantic,
        tr=tr_payload,
        feedback="Tighten filters",
    )
    assert metrics.metrics
    assert any("Tighten filters" in f for m in metrics.metrics for f in m.filters)


def test_pipeline_validation_detects_bad_dependency() -> None:
    pipeline = PipelineSpecificationPayload(
        name="bad",
        description="broken deps",
        stages=[
            PipelineStage(
                name="a",
                kind="ingest",
                description="ingest",
                inputs=[],
                outputs=["x"],
                dependencies=["missing"],
            )
        ],
    )
    results = validate_pipeline_specification(pipeline)
    assert any("FAIL:" in r and "unknown stage" in r for r in results)


def test_assemble_review_package_includes_validation() -> None:
    run_id = UUID("00000000-0000-0000-0000-000000000099")
    pinned = [
        ArtefactRef(
            artefact_id=UUID("00000000-0000-0000-0000-000000000001"),
            artefact_type=ArtefactType.BUSINESS_REQUIREMENT,
            version=1,
            run_id=run_id,
        )
    ]
    pkg = assemble_review_package(
        title="demo",
        pinned=pinned,
        validation_results=["PASS: ok"],
    )
    assert pkg.validation_results == ["PASS: ok"]
    assert pkg.decision_state == "pending_review"
    assert len(pkg.pinned_artefacts) == 1
