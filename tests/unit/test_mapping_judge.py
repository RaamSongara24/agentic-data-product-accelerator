"""Mapping Judge retry caps and escalation."""

from __future__ import annotations

from agentic_data_product.orchestration.mapping.judge import (
    JudgeOutcome,
    evaluate_mapping_proposal,
)


def test_judge_passes_valid_proposal() -> None:
    result = evaluate_mapping_proposal(
        discovered_object_ids=["analytics.sales.orders"],
        mapping_proposal={
            "source_object_ids": ["analytics.sales.orders"],
            "entities": [{"name": "Orders"}],
        },
        schema_retry_count=0,
        logic_retry_count=0,
        schema_retry_cap=2,
        logic_retry_cap=2,
    )
    assert result.outcome == JudgeOutcome.PASS


def test_schema_issue_retries_then_escalates() -> None:
    discovered = ["analytics.sales.orders"]
    bad = {"source_object_ids": [], "entities": [{"name": "X"}]}

    first = evaluate_mapping_proposal(
        discovered_object_ids=discovered,
        mapping_proposal=bad,
        schema_retry_count=0,
        logic_retry_count=0,
        schema_retry_cap=1,
        logic_retry_cap=2,
    )
    assert first.outcome == JudgeOutcome.SCHEMA_ISSUE
    assert first.schema_retry_count == 1

    second = evaluate_mapping_proposal(
        discovered_object_ids=discovered,
        mapping_proposal=bad,
        schema_retry_count=first.schema_retry_count,
        logic_retry_count=0,
        schema_retry_cap=1,
        logic_retry_cap=2,
    )
    assert second.outcome == JudgeOutcome.ESCALATE
    assert "exhausted" in second.notes.lower()


def test_logic_issue_retries_then_escalates() -> None:
    proposal = {
        "source_object_ids": ["analytics.sales.orders"],
        "entities": [],
    }
    first = evaluate_mapping_proposal(
        discovered_object_ids=["analytics.sales.orders"],
        mapping_proposal=proposal,
        schema_retry_count=0,
        logic_retry_count=0,
        schema_retry_cap=2,
        logic_retry_cap=1,
    )
    assert first.outcome == JudgeOutcome.LOGIC_ISSUE
    assert first.logic_retry_count == 1

    second = evaluate_mapping_proposal(
        discovered_object_ids=["analytics.sales.orders"],
        mapping_proposal=proposal,
        schema_retry_count=0,
        logic_retry_count=first.logic_retry_count,
        schema_retry_cap=2,
        logic_retry_cap=1,
    )
    assert second.outcome == JudgeOutcome.ESCALATE


def test_force_schema_issue_respects_cap() -> None:
    result = evaluate_mapping_proposal(
        discovered_object_ids=["a"],
        mapping_proposal={"source_object_ids": ["a"], "entities": [{"name": "A"}]},
        schema_retry_count=2,
        logic_retry_count=0,
        schema_retry_cap=2,
        logic_retry_cap=2,
        force_outcome="schema_issue",
    )
    assert result.outcome == JudgeOutcome.ESCALATE
