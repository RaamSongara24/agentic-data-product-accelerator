"""Authenticated user context for discovery and generation (no privilege elevation)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class UserContext(BaseModel):
    """Identity and optional explicit fixture visibility for discovery tools.

    When ``accessible_object_ids`` is omitted, fixture-mode discovery applies the
    catalogue ACL for ``user_id``. An explicit list is an allow-list override used
    by tests and demos — never a way to elevate beyond a live platform.
    """

    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1)
    accessible_object_ids: list[str] | None = None
