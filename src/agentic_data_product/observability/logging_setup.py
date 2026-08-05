"""Configure application logging."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from agentic_data_product.observability.errors import AppError


class JsonFormatter(logging.Formatter):
    """Minimal JSON log formatter for container-friendly output."""

    _SKIP_RECORD_ATTRS = frozenset(
        {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "message",
            "asctime",
            "taskName",
        }
    )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in self._SKIP_RECORD_ATTRS or key.startswith("_"):
                continue
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(*, level: str = "INFO", json_logs: bool = False) -> None:
    """Configure root logging once for the process."""
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level.upper())

    handler = logging.StreamHandler(sys.stdout)
    if json_logs:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    root.addHandler(handler)

    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def log_event(
    logger: logging.Logger,
    event: str,
    *,
    level: int = logging.INFO,
    **fields: Any,
) -> None:
    """Emit a structured application event (works with JSON and plain formatters)."""
    # Keep message human-readable; structured fields live on the LogRecord.
    extra = {"event": event, **fields}
    logger.log(level, event, extra=extra)


def log_app_error(
    logger: logging.Logger,
    exc: BaseException,
    *,
    level: int = logging.ERROR,
    **fields: Any,
) -> None:
    """Log an exception using the error taxonomy when available."""
    payload: dict[str, Any] = dict(fields)
    if isinstance(exc, AppError):
        payload.update(exc.to_log_fields())
    else:
        payload.setdefault("error_type", type(exc).__name__)
        payload.setdefault("error_message", str(exc))
    log_event(logger, "error", level=level, **payload)
