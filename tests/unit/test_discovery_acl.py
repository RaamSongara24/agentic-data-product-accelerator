"""Discovery fixture ACL — inaccessible objects never returned; fail closed."""

from __future__ import annotations

import pytest

from agentic_data_product.domain.user_context import UserContext
from agentic_data_product.integrations.discovery import (
    INACCESSIBLE_OBJECT_IDS,
    DiscoveryPermissionError,
    discover_accessible_objects,
    object_ids,
)
from agentic_data_product.observability.errors import ErrorCode
from agentic_data_product.orchestration.mapping.subgraph import _user_context_from_state
from agentic_data_product.orchestration.state import HitlGraphState


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


def test_discovery_without_user_context_fails_closed() -> None:
    with pytest.raises(DiscoveryPermissionError) as exc_info:
        discover_accessible_objects(None)
    assert exc_info.value.code == ErrorCode.DISCOVERY_USER_CONTEXT_REQUIRED


def test_discovery_with_blank_user_id_fails_closed() -> None:
    with pytest.raises(DiscoveryPermissionError):
        discover_accessible_objects(UserContext(user_id="   "))


def test_mapping_state_without_user_id_fails_closed() -> None:
    state: HitlGraphState = {"run_id": "00000000-0000-0000-0000-000000000099"}
    with pytest.raises(DiscoveryPermissionError) as exc_info:
        _user_context_from_state(state)
    assert exc_info.value.code == ErrorCode.DISCOVERY_USER_CONTEXT_REQUIRED
