"""Unit tests for HITL routing and review schemas."""

from __future__ import annotations

import pytest

from agentic_data_product.domain.enums import ReviewDecisionKind
from agentic_data_product.domain.review import ReviewDecisionRequest
from agentic_data_product.orchestration.graph import route_after_review
from agentic_data_product.orchestration.state import HitlGraphState


@pytest.mark.parametrize(
    ("decision", "expected"),
    [
        (ReviewDecisionKind.APPROVE, "approved"),
        (ReviewDecisionKind.REJECT, "terminated"),
        (ReviewDecisionKind.REQUEST_REVISIONS, "generate_stub"),
    ],
)
def test_route_after_review(decision: ReviewDecisionKind, expected: str) -> None:
    state: HitlGraphState = {"run_id": "00000000-0000-0000-0000-000000000001", "decision": decision}
    assert route_after_review(state) == expected


def test_route_after_review_rejects_unknown() -> None:
    state: HitlGraphState = {"run_id": "00000000-0000-0000-0000-000000000001", "decision": "noop"}
    with pytest.raises(ValueError, match="Unknown"):
        route_after_review(state)


def test_review_decision_request_schema() -> None:
    body = ReviewDecisionRequest(
        decision=ReviewDecisionKind.REQUEST_REVISIONS,
        comments="Please clarify objectives",
        reviewer_id="consultant-1",
    )
    assert body.decision == ReviewDecisionKind.REQUEST_REVISIONS
    assert "clarify" in body.comments
