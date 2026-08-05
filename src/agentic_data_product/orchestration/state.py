"""LangGraph state schema for the M2 HITL stub workflow."""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class HitlGraphState(TypedDict):
    """Control-plane state held in the checkpointer (artefact bodies live in the store)."""

    run_id: str
    title: NotRequired[str | None]
    created_by: NotRequired[str | None]
    seed_payload: NotRequired[dict[str, Any] | None]
    feedback: NotRequired[str | None]
    artefact_id: NotRequired[str | None]
    artefact_version: NotRequired[int | None]
    artefact_type: NotRequired[str | None]
    decision: NotRequired[str | None]
