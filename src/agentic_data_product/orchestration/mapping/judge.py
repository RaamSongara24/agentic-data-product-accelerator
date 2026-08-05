"""Mapping Judge: pass / schema / logic outcomes with retry-cap escalation."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class JudgeOutcome(StrEnum):
    PASS = "pass"
    SCHEMA_ISSUE = "schema_issue"
    LOGIC_ISSUE = "logic_issue"
    ESCALATE = "escalate"


class JudgeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: JudgeOutcome
    notes: str = ""
    schema_retry_count: int = Field(ge=0, default=0)
    logic_retry_count: int = Field(ge=0, default=0)


def evaluate_mapping_proposal(
    *,
    discovered_object_ids: list[str],
    mapping_proposal: dict[str, Any],
    schema_retry_count: int,
    logic_retry_count: int,
    schema_retry_cap: int,
    logic_retry_cap: int,
    force_outcome: str | None = None,
) -> JudgeResult:
    """Judge a mapping proposal; honour retry caps and optional test overrides.

    ``force_outcome`` (test-only) injects schema_issue / logic_issue / pass /
    escalate without inspecting the proposal.
    """
    if force_outcome:
        forced = JudgeOutcome(force_outcome)
        if forced == JudgeOutcome.SCHEMA_ISSUE:
            next_schema = schema_retry_count + 1
            if next_schema > schema_retry_cap:
                return JudgeResult(
                    outcome=JudgeOutcome.ESCALATE,
                    notes=(
                        f"Schema retry cap ({schema_retry_cap}) exhausted; "
                        "escalating last proposal to HITL."
                    ),
                    schema_retry_count=schema_retry_count,
                    logic_retry_count=logic_retry_count,
                )
            return JudgeResult(
                outcome=JudgeOutcome.SCHEMA_ISSUE,
                notes="Forced schema issue for retry testing.",
                schema_retry_count=next_schema,
                logic_retry_count=logic_retry_count,
            )
        if forced == JudgeOutcome.LOGIC_ISSUE:
            next_logic = logic_retry_count + 1
            if next_logic > logic_retry_cap:
                return JudgeResult(
                    outcome=JudgeOutcome.ESCALATE,
                    notes=(
                        f"Logic retry cap ({logic_retry_cap}) exhausted; "
                        "escalating last proposal to HITL."
                    ),
                    schema_retry_count=schema_retry_count,
                    logic_retry_count=logic_retry_count,
                )
            return JudgeResult(
                outcome=JudgeOutcome.LOGIC_ISSUE,
                notes="Forced logic issue for retry testing.",
                schema_retry_count=schema_retry_count,
                logic_retry_count=next_logic,
            )
        if forced == JudgeOutcome.ESCALATE:
            return JudgeResult(
                outcome=JudgeOutcome.ESCALATE,
                notes="Forced escalation.",
                schema_retry_count=schema_retry_count,
                logic_retry_count=logic_retry_count,
            )
        return JudgeResult(
            outcome=JudgeOutcome.PASS,
            notes="Forced pass.",
            schema_retry_count=schema_retry_count,
            logic_retry_count=logic_retry_count,
        )

    # Deterministic checks
    mapped_sources = mapping_proposal.get("source_object_ids") or []
    if not isinstance(mapped_sources, list) or not mapped_sources:
        next_schema = schema_retry_count + 1
        if next_schema > schema_retry_cap:
            return JudgeResult(
                outcome=JudgeOutcome.ESCALATE,
                notes="No source objects mapped; schema retries exhausted.",
                schema_retry_count=schema_retry_count,
                logic_retry_count=logic_retry_count,
            )
        return JudgeResult(
            outcome=JudgeOutcome.SCHEMA_ISSUE,
            notes="Mapping proposal missing source_object_ids.",
            schema_retry_count=next_schema,
            logic_retry_count=logic_retry_count,
        )

    unknown = [s for s in mapped_sources if s not in discovered_object_ids]
    if unknown:
        next_schema = schema_retry_count + 1
        if next_schema > schema_retry_cap:
            return JudgeResult(
                outcome=JudgeOutcome.ESCALATE,
                notes=f"Unknown sources {unknown}; schema retries exhausted.",
                schema_retry_count=schema_retry_count,
                logic_retry_count=logic_retry_count,
            )
        return JudgeResult(
            outcome=JudgeOutcome.SCHEMA_ISSUE,
            notes=f"Mapped sources not in discovery set: {unknown}",
            schema_retry_count=next_schema,
            logic_retry_count=logic_retry_count,
        )

    entities = mapping_proposal.get("entities") or []
    if not isinstance(entities, list) or len(entities) < 1:
        next_logic = logic_retry_count + 1
        if next_logic > logic_retry_cap:
            return JudgeResult(
                outcome=JudgeOutcome.ESCALATE,
                notes="No entities in proposal; logic retries exhausted.",
                schema_retry_count=schema_retry_count,
                logic_retry_count=logic_retry_count,
            )
        return JudgeResult(
            outcome=JudgeOutcome.LOGIC_ISSUE,
            notes="Mapping proposal has no target entities.",
            schema_retry_count=schema_retry_count,
            logic_retry_count=next_logic,
        )

    return JudgeResult(
        outcome=JudgeOutcome.PASS,
        notes="Mapping proposal accepted by judge.",
        schema_retry_count=schema_retry_count,
        logic_retry_count=logic_retry_count,
    )
