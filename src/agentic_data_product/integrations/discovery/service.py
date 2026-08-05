"""Fixture-mode discovery that filters catalogue objects by user context."""

from __future__ import annotations

from agentic_data_product.domain.user_context import UserContext
from agentic_data_product.integrations.discovery.fixtures import (
    FIXTURE_CATALOGUE,
    FixtureObject,
)


def discover_accessible_objects(
    user_context: UserContext,
    *,
    catalogue: tuple[FixtureObject, ...] | list[FixtureObject] = FIXTURE_CATALOGUE,
) -> list[FixtureObject]:
    """Return only objects the user may see (fixture ACL or explicit allow-list).

    Never elevates access: an explicit ``accessible_object_ids`` list can only
    further restrict visibility relative to the catalogue ACL for that principal.
    Objects absent from the catalogue ACL for the user are never returned.
    """
    acl_visible = [obj for obj in catalogue if user_context.user_id in obj.allowed_principals]
    if user_context.accessible_object_ids is None:
        return list(acl_visible)

    allow = set(user_context.accessible_object_ids)
    # Intersect with ACL — explicit list cannot grant inaccessible objects.
    return [obj for obj in acl_visible if obj.object_id in allow]


def object_ids(objects: list[FixtureObject]) -> list[str]:
    return [obj.object_id for obj in objects]
