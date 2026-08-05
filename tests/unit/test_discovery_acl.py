"""Discovery fixture ACL — inaccessible objects never returned."""

from __future__ import annotations

from agentic_data_product.domain.user_context import UserContext
from agentic_data_product.integrations.discovery import (
    INACCESSIBLE_OBJECT_IDS,
    discover_accessible_objects,
    object_ids,
)


def test_consultant_never_sees_restricted_objects() -> None:
    ctx = UserContext(user_id="consultant")
    visible = discover_accessible_objects(ctx)
    ids = object_ids(visible)

    assert "analytics.sales.orders" in ids
    assert "analytics.sales.customers" in ids
    for forbidden in INACCESSIBLE_OBJECT_IDS:
        assert forbidden not in ids


def test_explicit_allow_list_cannot_elevate() -> None:
    """Passing an inaccessible id in accessible_object_ids must not grant it."""
    ctx = UserContext(
        user_id="consultant",
        accessible_object_ids=[
            "analytics.sales.orders",
            "hr.payroll.salaries",  # not on consultant ACL
        ],
    )
    ids = object_ids(discover_accessible_objects(ctx))
    assert ids == ["analytics.sales.orders"]
    assert "hr.payroll.salaries" not in ids


def test_hr_admin_sees_salaries_only_via_acl() -> None:
    ctx = UserContext(user_id="hr_admin")
    ids = object_ids(discover_accessible_objects(ctx))
    assert "hr.payroll.salaries" in ids
    assert "analytics.sales.orders" not in ids
