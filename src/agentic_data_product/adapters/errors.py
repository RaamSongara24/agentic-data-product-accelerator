"""Adapter-specific errors."""

from __future__ import annotations

from agentic_data_product.observability.errors import AppError, ErrorCode


class AdapterError(AppError):
    """Base error for platform adapter operations."""

    code = ErrorCode.ADAPTER_ERROR


class AdapterApprovalRequiredError(AdapterError):
    """Raised when artefacts are not approved for materialisation."""

    code = ErrorCode.ADAPTER_APPROVAL_REQUIRED


class AdapterInputError(AdapterError):
    """Raised when required approved artefact types are missing or invalid."""

    code = ErrorCode.ADAPTER_INPUT_INVALID
