"""Engineer Agent: produce canonical Pipeline Specification (no vendor DSL)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from agentic_data_product.domain.artefacts import (
    DataModelPayload,
    PipelineSpecificationPayload,
    PipelineStage,
    SemanticModelPayload,
    TechnicalRequirementPayload,
)
from agentic_data_product.integrations.llm.base import LlmClient, LlmMessage

logger = logging.getLogger(__name__)

GOLDEN_PIPELINE_NAME_PREFIX = "Pipeline specification for:"


def generate_pipeline_specification_deterministic(
    *,
    tr: TechnicalRequirementPayload,
    semantic: SemanticModelPayload,
    data_model: DataModelPayload,
    feedback: str | None = None,
) -> PipelineSpecificationPayload:
    """Declarative pipeline stages derived from approved modelling artefacts."""
    source_ids = list(data_model.mapping_context.get("source_object_ids") or [])
    ingest_inputs = source_ids or ["approved_source_catalogue"]
    entity_names = [e.name for e in data_model.entities]

    stages = [
        PipelineStage(
            name="ingest_sources",
            kind="ingest",
            description="Ingest permitted source objects into a staging area",
            inputs=ingest_inputs,
            outputs=["staging.raw_sales"],
            dependencies=[],
        ),
        PipelineStage(
            name="transform_star_schema",
            kind="transform",
            description=(
                f"Transform staging data into logical entities: {', '.join(entity_names)}"
            ),
            inputs=["staging.raw_sales"],
            outputs=[f"curated.{n}" for n in entity_names[:4]] or ["curated.FactOrder"],
            dependencies=["ingest_sources"],
        ),
        PipelineStage(
            name="validate_quality",
            kind="validate",
            description="Apply declarative data-quality and grain checks",
            inputs=[f"curated.{n}" for n in entity_names[:4]] or ["curated.FactOrder"],
            outputs=["validated.star_schema"],
            dependencies=["transform_star_schema"],
        ),
        PipelineStage(
            name="publish_semantic",
            kind="publish",
            description=f"Publish semantic metrics for '{semantic.name}'",
            inputs=["validated.star_schema"],
            outputs=["publish.semantic_ready"],
            dependencies=["validate_quality"],
        ),
    ]

    validation_rules = [
        "Primary keys must be non-null on FactOrder and dimension entities",
        "Foreign keys from FactOrder to dimensions must resolve",
        "Measures must match approved semantic metric names",
    ]
    validation_rules.extend(f"Cover behaviour: {b}" for b in tr.behaviours[:2])
    if feedback:
        validation_rules.append(f"Incorporate reviewer feedback: {feedback}")

    return PipelineSpecificationPayload(
        name=f"{GOLDEN_PIPELINE_NAME_PREFIX} {semantic.name}",
        description=(
            "Technology-agnostic pipeline specification for the approved data product "
            "(ingest → transform → validate → publish)."
        ),
        stages=stages,
        orchestration_notes="Linear DAG; no parallel branches in MVP path",
        validation_rules=validation_rules,
        operational_behaviour={
            "schedule": "on_demand",
            "retry_policy": "none_in_mvp",
        },
        lineage_notes=[
            "Each stage records input/output dataset names for Review Package traceability",
            f"Derived from semantic model '{semantic.name}' and data model '{data_model.name}'",
        ],
    )


def _parse_pipeline_json(raw: str) -> PipelineSpecificationPayload:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    if not isinstance(data, dict):
        msg = "LLM pipeline response was not a JSON object"
        raise TypeError(msg)
    return PipelineSpecificationPayload.model_validate(data)


async def generate_pipeline_specification(
    *,
    tr: TechnicalRequirementPayload,
    semantic: SemanticModelPayload,
    data_model: DataModelPayload,
    llm: LlmClient,
    feedback: str | None = None,
) -> PipelineSpecificationPayload:
    """Produce a Pipeline Specification from approved modelling artefacts."""
    if llm.provider_name == "deterministic":
        return generate_pipeline_specification_deterministic(
            tr=tr,
            semantic=semantic,
            data_model=data_model,
            feedback=feedback,
        )

    system = (
        "You are a data engineer agent for an Agentic Data Product Design Platform. "
        "Return ONLY a JSON object matching the Pipeline Specification schema. "
        "Stages must be declarative and technology-agnostic. Do not emit vendor job code."
    )
    user_payload: dict[str, Any] = {
        "technical_requirement": tr.model_dump(mode="json"),
        "semantic_model": semantic.model_dump(mode="json"),
        "data_model": data_model.model_dump(mode="json"),
        "feedback": feedback,
    }
    messages = [
        LlmMessage(role="system", content=system),
        LlmMessage(role="user", content=json.dumps(user_payload)),
    ]
    try:
        raw = await llm.complete(messages, temperature=0.0)
        return _parse_pipeline_json(raw)
    except Exception:
        logger.exception("LLM pipeline generation failed; using deterministic fallback")
        return generate_pipeline_specification_deterministic(
            tr=tr,
            semantic=semantic,
            data_model=data_model,
            feedback=feedback,
        )
