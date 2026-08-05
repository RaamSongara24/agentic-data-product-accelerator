"""Unit tests for error taxonomy and structured logging helpers."""

from __future__ import annotations

import json
import logging

import pytest

from agentic_data_product.observability.errors import AppError, ErrorCode
from agentic_data_product.observability.logging_setup import JsonFormatter, log_app_error, log_event


def test_app_error_to_log_fields() -> None:
    err = AppError(
        "boom",
        code=ErrorCode.VALIDATION_ERROR,
        context={"field": "user_id"},
    )
    fields = err.to_log_fields()
    assert fields["error_code"] == "validation_error"
    assert fields["error_context"]["field"] == "user_id"


def test_json_formatter_includes_structured_extras() -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.event = "discovery_completed"  # type: ignore[attr-defined]
    record.run_id = "run-1"  # type: ignore[attr-defined]
    payload = json.loads(JsonFormatter().format(record))
    assert payload["event"] == "discovery_completed"
    assert payload["run_id"] == "run-1"
    assert payload["message"] == "hello"


def test_log_event_and_log_app_error(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("agentic_data_product.test_errors")
    with caplog.at_level(logging.INFO, logger=logger.name):
        log_event(logger, "node_started", run_id="abc")
        log_app_error(
            logger,
            AppError("denied", code=ErrorCode.DISCOVERY_USER_CONTEXT_REQUIRED),
            run_id="abc",
        )
    assert any("node_started" in r.message for r in caplog.records)
    assert any(
        getattr(r, "error_code", None) == "discovery_user_context_required" for r in caplog.records
    )
