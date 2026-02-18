"""Structured JSON logging configuration for the application."""

import logging
from contextvars import ContextVar

from pythonjsonlogger.json import JsonFormatter as _JsonFormatter

from app.config import settings

# Per-request correlation ID — set by RequestIdMiddleware, read by _RequestIdFilter
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class _RequestIdFilter(logging.Filter):
    """Injects the current request_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class _AppJsonFormatter(_JsonFormatter):
    """Extends the standard JSON formatter with service-level metadata."""

    def add_fields(
        self,
        log_record: dict[str, object],
        record: logging.LogRecord,
        message_dict: dict[str, object],
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record.setdefault("service", settings.app_name)
        log_record.setdefault("version", settings.app_version)
        log_record.setdefault("env", settings.env)


def configure_logging() -> None:
    """Set up structured JSON logging for the entire application.

    Call once at application startup (inside create_app) before any other
    module creates a logger so that all handlers are consistently configured.

    Log levels:
        DEBUG  — read operations, DB query details (enabled when settings.debug=True)
        INFO   — every mutating operation, startup/shutdown, state transitions
        WARNING — invalid transition attempts, unexpected-but-handled conditions
        ERROR  — unhandled exceptions, rollbacks, infrastructure failures
        CRITICAL — unrecoverable startup failures
    """
    log_level = logging.DEBUG if settings.debug else logging.INFO

    handler = logging.StreamHandler()
    handler.setFormatter(
        _AppJsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s %(request_id)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        )
    )
    handler.addFilter(_RequestIdFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level)

    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
