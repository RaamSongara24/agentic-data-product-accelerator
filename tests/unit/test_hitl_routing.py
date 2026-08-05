"""Unit tests for HITL routing and review schemas."""

from __future__ import annotations

import pytest

from agentic_data_product.domain.enums import ReviewDecisionKind
from agentic_data_product.domain.review import ReviewDecisionRequest
from agentic_data_product.orchestration.graph import (
    route_after_implementation_review,
    route_after_mapping_review,
    route_after_modelling_review,
    route_after_rp_review,
    route_after_tr_review,
)
from agentic_data_product.orchestration.state import HitlGraphState


@pytest.mark.parametrize(
    ("decision", "expected"),
    [
        (ReviewDecisionKind.APPROVE, "mapping_discovery"),
        (ReviewDecisionKind.REJECT, "terminated"),
        (ReviewDecisionKind.REQUEST_REVISIONS, "generate_tr"),
    ],
)
def test_route_after_tr_review(decision: ReviewDecisionKind, expected: str) -> None:
    state: HitlGraphState = {"run_id": "00000000-0000-0000-0000-000000000001", "decision": decision}
    assert route_after_tr_review(state) == expected


@pytest.mark.parametrize(
    ("decision", "expected"),
    [
        (ReviewDecisionKind.APPROVE, "modelling"),
        (ReviewDecisionKind.REJECT, "terminated"),
        (ReviewDecisionKind.REQUEST_REVISIONS, "mapping_discovery"),
    ],
)
def test_route_after_mapping_review(decision: ReviewDecisionKind, expected: str) -> None:
    state: HitlGraphState = {"run_id": "00000000-0000-0000-0000-000000000001", "decision": decision}
    assert route_after_mapping_review(state) == expected


@pytest.mark.parametrize(
    ("decision", "expected"),
    [
        (ReviewDecisionKind.APPROVE, "implementation"),
        (ReviewDecisionKind.REJECT, "terminated"),
        (ReviewDecisionKind.REQUEST_REVISIONS, "modelling"),
    ],
)
def test_route_after_modelling_review(decision: ReviewDecisionKind, expected: str) -> None:
    state: HitlGraphState = {"run_id": "00000000-0000-0000-0000-000000000001", "decision": decision}
    assert route_after_modelling_review(state) == expected


@pytest.mark.parametrize(
    ("decision", "expected"),
    [
        (ReviewDecisionKind.APPROVE, "assemble_rp"),
        (ReviewDecisionKind.REJECT, "terminated"),
        (ReviewDecisionKind.REQUEST_REVISIONS, "generate_metrics"),
    ],
)
def test_route_after_implementation_review(decision: ReviewDecisionKind, expected: str) -> None:
    state: HitlGraphState = {"run_id": "00000000-0000-0000-0000-000000000001", "decision": decision}
    assert route_after_implementation_review(state) == expected


@pytest.mark.parametrize(
    ("decision", "expected"),
    [
        (ReviewDecisionKind.APPROVE, "approved"),
        (ReviewDecisionKind.REJECT, "terminated"),
        (ReviewDecisionKind.REQUEST_REVISIONS, "assemble_rp"),
    ],
)
def test_route_after_rp_review(decision: ReviewDecisionKind, expected: str) -> None:
    state: HitlGraphState = {"run_id": "00000000-0000-0000-0000-000000000001", "decision": decision}
    assert route_after_rp_review(state) == expected


def test_route_after_tr_review_rejects_unknown() -> None:
    state: HitlGraphState = {"run_id": "00000000-0000-0000-0000-000000000001", "decision": "noop"}
    with pytest.raises(ValueError, match="Unknown"):
        route_after_tr_review(state)


def test_review_decision_request_schema() -> None:
    body = ReviewDecisionRequest(
        decision=ReviewDecisionKind.REQUEST_REVISIONS,
        comments="Please clarify objectives",
        reviewer_id="consultant-1",
    )
    assert body.decision == ReviewDecisionKind.REQUEST_REVISIONS
    assert "clarify" in body.comments
