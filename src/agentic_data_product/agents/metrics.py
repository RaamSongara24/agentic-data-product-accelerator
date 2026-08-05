"""Metrics Agent: produce portable Metric Definitions from the Semantic Model."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from agentic_data_product.domain.artefacts import (
    MetricDefinition,
    MetricDefinitionsPayload,
    SemanticModelPayload,
    TechnicalRequirementPayload,
)
from agentic_data_product.integrations.llm.base import LlmClient, LlmMessage

logger = logging.getLogger(__name__)

GOLDEN_METRICS_NAME_PREFIX = "Metric definitions for:"


def generate_metric_definitions_deterministic(
    *,
    semantic: SemanticModelPayload,
    tr: TechnicalRequirementPayload | None = None,
    feedback: str | None = None,
) -> MetricDefinitionsPayload:
    """Portable KPI definitions aligned to semantic metrics."""
    metrics: list[MetricDefinition] = []
    for sm in semantic.metrics:
        aggregation = "sum"
        lowered = sm.name.lower()
        if "count" in lowered:
            aggregation = "count"
        elif "avg" in lowered or "average" in lowered:
            aggregation = "avg"
        calc = f"{aggregation.upper()}({sm.name})"
        grain = sm.grain or "order"
        filters: list[str] = []
        if tr is not None:
            filters.extend(f"Respect constraint: {c}" for c in tr.governance_requirements[:1])
        if feedback:
            filters.append(f"Incorporate reviewer feedback: {feedback}")
        metrics.append(
            MetricDefinition(
                name=sm.name,
                description=sm.definition,
                calculation=calc,
                aggregation=aggregation,
                filters=filters,
                grain=grain,
                business_logic=semantic.business_definitions.get(sm.name),
            )
        )

    if not metrics:
        metrics.append(
            MetricDefinition(
                name="order_count",
                description="Fallback order count metric",
                calculation="COUNT(order_sk)",
                aggregation="count",
                filters=[],
                grain="order",
            )
        )

    description = f"Portable metric definitions for semantic model '{semantic.name}'"
    if feedback:
        description = f"{description}; revised per feedback"

    return MetricDefinitionsPayload(
        name=f"{GOLDEN_METRICS_NAME_PREFIX} {semantic.name}",
        description=description,
        metrics=metrics,
    )


def _parse_metrics_json(raw: str) -> MetricDefinitionsPayload:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    if not isinstance(data, dict):
        msg = "LLM metrics response was not a JSON object"
        raise TypeError(msg)
    return MetricDefinitionsPayload.model_validate(data)


async def generate_metric_definitions(
    *,
    semantic: SemanticModelPayload,
    tr: TechnicalRequirementPayload | None = None,
    llm: LlmClient,
    feedback: str | None = None,
) -> MetricDefinitionsPayload:
    """Produce Metric Definitions from an approved Semantic Model."""
    if llm.provider_name == "deterministic":
        return generate_metric_definitions_deterministic(
            semantic=semantic,
            tr=tr,
            feedback=feedback,
        )

    system = (
        "You are a metrics agent for an Agentic Data Product Design Platform. "
        "Return ONLY a JSON object matching the Metric Definitions schema. "
        "Definitions must be portable and technology-agnostic. Do not invent metrics "
        "from inaccessible source objects."
    )
    user_payload: dict[str, Any] = {
        "semantic_model": semantic.model_dump(mode="json"),
        "technical_requirement": tr.model_dump(mode="json") if tr else None,
        "feedback": feedback,
    }
    messages = [
        LlmMessage(role="system", content=system),
        LlmMessage(role="user", content=json.dumps(user_payload)),
    ]
    try:
        raw = await llm.complete(messages, temperature=0.0)
        return _parse_metrics_json(raw)
    except Exception:
        logger.exception("LLM metrics generation failed; using deterministic fallback")
        return generate_metric_definitions_deterministic(
            semantic=semantic,
            tr=tr,
            feedback=feedback,
        )
