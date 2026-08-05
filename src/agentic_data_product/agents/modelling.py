"""Modelling Agent: Technical Requirement + mapping → Semantic Model + Data Model."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from agentic_data_product.domain.artefacts import (
    DataAttribute,
    DataEntity,
    DataModelPayload,
    DataRelationship,
    GovernanceMetadata,
    SemanticDimension,
    SemanticMetric,
    SemanticModelPayload,
    SemanticRelationship,
    TechnicalRequirementPayload,
)
from agentic_data_product.integrations.llm.base import LlmClient, LlmMessage

logger = logging.getLogger(__name__)

GOLDEN_SEMANTIC_NAME_PREFIX = "Semantic model for:"


def _measure_definition(name: str) -> str:
    pretty = name.replace("_", " ")
    return f"Business measure '{pretty}' derived from approved technical requirements"


def _dimension_definition(name: str) -> str:
    return f"Dimensional attribute '{name}' for analytical slicing"


def generate_modelling_deterministic(
    tr: TechnicalRequirementPayload,
    *,
    mapping_data_model: DataModelPayload | None = None,
    feedback: str | None = None,
) -> tuple[SemanticModelPayload, DataModelPayload]:
    """Heuristic Kimball-oriented Semantic + Data Model for golden tests."""
    metrics = [
        SemanticMetric(name=m, definition=_measure_definition(m), grain="order")
        for m in (tr.candidate_measures or ["order_amount", "order_count"])
    ]
    dimensions = [
        SemanticDimension(
            name=d,
            definition=_dimension_definition(d),
            hierarchy=[d, "All"] if d.lower() != "date" else ["Day", "Month", "Year"],
        )
        for d in (tr.candidate_dimensions or ["Customer", "Product", "Date"])
    ]
    relationships = [
        SemanticRelationship(
            from_entity="FactOrder",
            to_entity=d.name,
            cardinality="many_to_one",
            description=f"FactOrder references dimension {d.name}",
        )
        for d in dimensions
    ]

    business_definitions = {
        "fact": ", ".join(tr.candidate_facts) or "fact_order",
        "intent": tr.summary,
    }
    if feedback:
        business_definitions["reviewer_feedback"] = feedback

    semantic = SemanticModelPayload(
        name=f"{GOLDEN_SEMANTIC_NAME_PREFIX} {tr.summary.split(':', 1)[-1].strip()}",
        description=(
            "Kimball-oriented semantic model produced from approved technical "
            "requirements and mapping context."
        ),
        metrics=metrics,
        dimensions=dimensions,
        relationships=relationships,
        business_definitions=business_definitions,
    )

    # Enrich mapping slice into a star-schema Data Model when mapping is present.
    entities: list[DataEntity] = []
    data_relationships: list[DataRelationship] = []
    mapping_context: dict[str, Any] = {}
    governance = GovernanceMetadata(
        access_notes=["Propagated from mapping / source visibility where available"],
    )

    if mapping_data_model is not None:
        mapping_context = dict(mapping_data_model.mapping_context)
        governance = mapping_data_model.governance_metadata or governance
        # Keep mapping entities and add dimensional / fact structure.
        entities.extend(mapping_data_model.entities)
        data_relationships.extend(mapping_data_model.relationships)

    fact_attrs = [
        DataAttribute(name="order_sk", data_type="string", nullable=False),
        DataAttribute(name="order_amount", data_type="decimal", nullable=False),
        DataAttribute(name="order_count", data_type="integer", nullable=False),
    ]
    for dim in dimensions:
        key = f"{dim.name.lower()}_sk"
        fact_attrs.append(DataAttribute(name=key, data_type="string", nullable=False))
        dim_entity_name = f"Dim{dim.name}"
        if not any(e.name == dim_entity_name for e in entities):
            entities.append(
                DataEntity(
                    name=dim_entity_name,
                    description=dim.definition,
                    attributes=[
                        DataAttribute(name=key, data_type="string", nullable=False),
                        DataAttribute(name=f"{dim.name.lower()}_name", data_type="string"),
                    ],
                    primary_key=[key],
                )
            )
        data_relationships.append(
            DataRelationship(
                from_entity="FactOrder",
                to_entity=dim_entity_name,
                from_keys=[key],
                to_keys=[key],
                cardinality="many_to_one",
            )
        )

    if not any(e.name == "FactOrder" for e in entities):
        entities.insert(
            0,
            DataEntity(
                name="FactOrder",
                description="Central fact for sales / order analytics",
                attributes=fact_attrs,
                primary_key=["order_sk"],
            ),
        )

    if feedback:
        mapping_context["modelling_feedback"] = feedback

    data_model = DataModelPayload(
        name="Sales star schema data model",
        description=(
            "Logical star-schema data model realising the semantic model (Kimball conventions)."
        ),
        entities=entities,
        relationships=data_relationships,
        mapping_context=mapping_context,
        governance_metadata=governance,
    )
    return semantic, data_model


def _parse_modelling_json(raw: str) -> tuple[SemanticModelPayload, DataModelPayload]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    if not isinstance(data, dict):
        msg = "LLM modelling response was not a JSON object"
        raise TypeError(msg)
    semantic = SemanticModelPayload.model_validate(data["semantic_model"])
    data_model = DataModelPayload.model_validate(data["data_model"])
    return semantic, data_model


async def generate_modelling_artefacts(
    tr: TechnicalRequirementPayload,
    *,
    mapping_data_model: DataModelPayload | None = None,
    llm: LlmClient,
    feedback: str | None = None,
) -> tuple[SemanticModelPayload, DataModelPayload]:
    """Produce Semantic Model and Data Model from TR (+ optional mapping slice)."""
    if llm.provider_name == "deterministic":
        return generate_modelling_deterministic(
            tr,
            mapping_data_model=mapping_data_model,
            feedback=feedback,
        )

    system = (
        "You are a dimensional modelling agent for an Agentic Data Product Design Platform. "
        "Return ONLY a JSON object with keys semantic_model and data_model matching the "
        "canonical Pydantic schemas. Use Kimball/star-schema conventions. "
        "Do not emit vendor DSLs or SQL."
    )
    user_payload: dict[str, Any] = {
        "technical_requirement": tr.model_dump(mode="json"),
        "mapping_data_model": (
            mapping_data_model.model_dump(mode="json") if mapping_data_model else None
        ),
        "feedback": feedback,
    }
    messages = [
        LlmMessage(role="system", content=system),
        LlmMessage(role="user", content=json.dumps(user_payload)),
    ]
    try:
        raw = await llm.complete(messages, temperature=0.0)
        return _parse_modelling_json(raw)
    except Exception:
        logger.exception("LLM modelling generation failed; using deterministic fallback")
        return generate_modelling_deterministic(
            tr,
            mapping_data_model=mapping_data_model,
            feedback=feedback,
        )
