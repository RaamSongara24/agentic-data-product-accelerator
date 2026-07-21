"""Unit tests for canonical domain models."""

from uuid import uuid4

from agentic_data_product.domain import (
    ArtefactType,
    BusinessRequirement,
    CanonicalArtefact,
    MetricDefinition,
    MetricDefinitions,
    WorkflowRun,
    WorkflowRunStatus,
    validate_payload,
)


def test_business_requirement_validation() -> None:
    model = BusinessRequirement(
        intent="Deliver monthly sales reporting",
        objectives=["Produce reconciled KPIs"],
        constraints=["Use governed sources only"],
        success_criteria=["Published report accepted by finance"],
    )
    assert model.intent.startswith("Deliver")
    assert model.objectives


def test_metric_definitions_validation() -> None:
    metrics = MetricDefinitions(
        definitions=[
            MetricDefinition(
                name="revenue",
                calculation="SUM(amount)",
                aggregation_rule="sum",
                grain="daily",
                business_logic="Gross revenue before discounts",
            )
        ]
    )
    assert metrics.definitions[0].name == "revenue"


def test_canonical_artefact_envelope() -> None:
    run_id = uuid4()
    artefact = CanonicalArtefact(
        run_id=run_id,
        artefact_type=ArtefactType.BUSINESS_REQUIREMENT,
        payload={"intent": "x", "objectives": [], "constraints": [], "success_criteria": []},
    )
    assert artefact.run_id == run_id
    assert artefact.version == 1


def test_workflow_run_defaults() -> None:
    run = WorkflowRun(name="test-run")
    assert run.status == WorkflowRunStatus.CREATED


def test_validate_payload_serializes() -> None:
    payload = validate_payload(
        ArtefactType.BUSINESS_REQUIREMENT,
        {
            "intent": "Improve finance reporting",
            "objectives": ["Consistency"],
            "constraints": ["Use approved sources"],
            "success_criteria": ["Approved by owner"],
        },
    )
    assert payload["intent"] == "Improve finance reporting"
