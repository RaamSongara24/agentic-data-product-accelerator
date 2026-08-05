"""Application error taxonomy with stable codes for APIs and structured logs."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    """Stable machine-readable error codes (HTTP mapping is separate)."""

    # Persistence / store
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    STORE_ERROR = "store_error"

    # HITL / runner
    INVALID_RUN_STATE = "invalid_run_state"
    HITL_ERROR = "hitl_error"

    # Discovery / security
    DISCOVERY_PERMISSION_DENIED = "discovery_permission_denied"
    DISCOVERY_USER_CONTEXT_REQUIRED = "discovery_user_context_required"

    # Adapters
    ADAPTER_ERROR = "adapter_error"
    ADAPTER_APPROVAL_REQUIRED = "adapter_approval_required"
    ADAPTER_INPUT_INVALID = "adapter_input_invalid"

    # Generic
    VALIDATION_ERROR = "validation_error"
    INTERNAL_ERROR = "internal_error"


class AppError(Exception):
    """Base application error carrying a stable ``ErrorCode`` and optional context."""

    code: ErrorCode = ErrorCode.INTERNAL_ERROR

    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code
        self.context: dict[str, Any] = dict(context or {})

    def to_log_fields(self) -> dict[str, Any]:
        """Fields suitable for structured logging (no secrets)."""
        fields: dict[str, Any] = {
            "error_code": self.code.value,
            "error_type": type(self).__name__,
            "error_message": str(self),
        }
        if self.context:
            fields["error_context"] = self.context
        return fields
