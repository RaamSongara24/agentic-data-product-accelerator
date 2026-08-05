"""Fixture-first source discovery (permission-filtered catalogue)."""

from agentic_data_product.integrations.discovery.fixtures import (
    FIXTURE_CATALOGUE,
    INACCESSIBLE_OBJECT_IDS,
    FixtureColumn,
    FixtureObject,
)
from agentic_data_product.integrations.discovery.service import (
    DiscoveryPermissionError,
    discover_accessible_objects,
    object_ids,
)

__all__ = [
    "FIXTURE_CATALOGUE",
    "INACCESSIBLE_OBJECT_IDS",
    "DiscoveryPermissionError",
    "FixtureColumn",
    "FixtureObject",
    "discover_accessible_objects",
    "object_ids",
]
