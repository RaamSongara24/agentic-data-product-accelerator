"""Fixture-mode discovery that filters catalogue objects by user context."""

from __future__ import annotations

from agentic_data_product.domain.user_context import UserContext
from agentic_data_product.integrations.discovery.fixtures import (
    FIXTURE_CATALOGUE,
    FixtureObject,
)
from agentic_data_product.observability.errors import AppError, ErrorCode


class DiscoveryPermissionError(AppError):
    """Raised when discovery cannot proceed safely (fail closed)."""

    code = ErrorCode.DISCOVERY_PERMISSION_DENIED


def discover_accessible_objects(
    user_context: UserContext | None,
    *,
    catalogue: tuple[FixtureObject, ...] | list[FixtureObject] = FIXTURE_CATALOGUE,
) -> list[FixtureObject]:
    """Return only objects the user may see (fixture ACL or explicit allow-list).

    Fail closed: discovery without authenticated user context raises
    ``DiscoveryPermissionError`` — never invents a default principal or returns
    the full catalogue.

    Never elevates access: an explicit ``accessible_object_ids`` list can only
    further restrict visibility relative to the catalogue ACL for that principal.
    Objects absent from the catalogue ACL for the user are never returned.
    """
    if user_context is None or not user_context.user_id.strip():
        raise DiscoveryPermissionError(
            "Discovery requires authenticated user context",
            code=ErrorCode.DISCOVERY_USER_CONTEXT_REQUIRED,
            context={"reason": "missing_user_context"},
        )

    acl_visible = [obj for obj in catalogue if user_context.user_id in obj.allowed_principals]
    if user_context.accessible_object_ids is None:
        return list(acl_visible)

    allow = set(user_context.accessible_object_ids)
    # Intersect with ACL — explicit list cannot grant inaccessible objects.
    return [obj for obj in acl_visible if obj.object_id in allow]


def object_ids(objects: list[FixtureObject]) -> list[str]:
    return [obj.object_id for obj in objects]
