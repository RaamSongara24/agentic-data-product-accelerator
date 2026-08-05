"""Requirements Agent: Business Requirement → Technical Requirement."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from agentic_data_product.domain.artefacts import (
    BusinessRequirementPayload,
    TechnicalRequirementPayload,
)
from agentic_data_product.integrations.llm.base import LlmClient, LlmMessage

logger = logging.getLogger(__name__)

# Stable tokens used by golden tests (deterministic path).
GOLDEN_TR_SUMMARY_PREFIX = "Technical specification for:"
GOLDEN_REQUIRED_BEHAVIOURS = (
    "Persist and version canonical artefacts for the requested data product",
    "Support human review of generated technical requirements before mapping",
)


def _slug_tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-zA-Z0-9]+", text.lower()) if len(t) > 2]


def _derive_entities(br: BusinessRequirementPayload) -> list[str]:
    entities: list[str] = []
    for objective in br.objectives:
        tokens = _slug_tokens(objective)
        for candidate in ("order", "customer", "product", "sale", "region", "metric"):
            if candidate in tokens and candidate.title() not in entities:
                entities.append(candidate.title())
    if not entities:
        entities = ["PrimaryEntity"]
    return entities


def _derive_candidates(
    br: BusinessRequirementPayload,
    entities: list[str],
) -> tuple[list[str], list[str], list[str]]:
    facts = [f"fact_{e.lower()}" for e in entities if e.lower() in {"order", "sale"}]
    if not facts:
        facts = [f"fact_{entities[0].lower()}"]
    dimensions = [e for e in entities if e.lower() in {"customer", "product", "region", "date"}]
    if "Date" not in dimensions:
        dimensions.append("Date")
    measures = ["order_amount", "order_count"]
    if (
        any("revenue" in o.lower() or "amount" in o.lower() for o in br.objectives)
        and "revenue" not in measures
    ):
        measures.insert(0, "revenue")
    return facts, dimensions, measures


def generate_technical_requirement_deterministic(
    br: BusinessRequirementPayload,
    *,
    feedback: str | None = None,
) -> TechnicalRequirementPayload:
    """Heuristic BR → TR mapping used for golden tests and default provider."""
    entities = _derive_entities(br)
    facts, dimensions, measures = _derive_candidates(br, entities)
    behaviours = list(GOLDEN_REQUIRED_BEHAVIOURS)
    behaviours.append(f"Address business intent: {br.intent[:200]}")
    if feedback:
        behaviours.append(f"Incorporate reviewer feedback: {feedback}")

    transformations = [f"Map source attributes into logical entity '{e}'" for e in entities]
    governance = list(br.constraints) or [
        "Respect source-platform permissions; do not use inaccessible objects",
    ]
    acceptance = list(br.success_criteria) or [
        "Technical Requirement reviewed and approved via HITL",
    ]

    return TechnicalRequirementPayload(
        summary=f"{GOLDEN_TR_SUMMARY_PREFIX} {br.title}",
        behaviours=behaviours,
        entities=entities,
        transformations=transformations,
        governance_requirements=governance,
        acceptance_criteria=acceptance,
        candidate_facts=facts,
        candidate_dimensions=dimensions,
        candidate_measures=measures,
    )


def _parse_tr_json(raw: str) -> TechnicalRequirementPayload:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    if not isinstance(data, dict):
        msg = "LLM TR response was not a JSON object"
        raise TypeError(msg)
    return TechnicalRequirementPayload.model_validate(data)


async def generate_technical_requirement(
    br: BusinessRequirementPayload,
    *,
    llm: LlmClient,
    feedback: str | None = None,
) -> TechnicalRequirementPayload:
    """Produce a Technical Requirement from a Business Requirement.

    Deterministic provider uses the heuristic path (golden-test stable).
    Other providers ask the LLM for a JSON payload matching the TR schema,
    falling back to deterministic on parse failure.
    """
    if llm.provider_name == "deterministic":
        return generate_technical_requirement_deterministic(br, feedback=feedback)

    system = (
        "You are a requirements analyst for an Agentic Data Product Design Platform. "
        "Return ONLY a JSON object matching the Technical Requirement schema fields: "
        "summary, behaviours, entities, transformations, governance_requirements, "
        "acceptance_criteria, candidate_facts, candidate_dimensions, candidate_measures. "
        "Do not emit vendor DSLs or SQL."
    )
    user_payload: dict[str, Any] = {
        "business_requirement": br.model_dump(mode="json"),
        "feedback": feedback,
    }
    messages = [
        LlmMessage(role="system", content=system),
        LlmMessage(role="user", content=json.dumps(user_payload)),
    ]
    try:
        raw = await llm.complete(messages, temperature=0.0)
        return _parse_tr_json(raw)
    except Exception:
        logger.exception(
            "LLM Technical Requirement generation failed; using deterministic fallback"
        )
        return generate_technical_requirement_deterministic(br, feedback=feedback)
