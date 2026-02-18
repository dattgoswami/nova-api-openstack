# Logging & Observability Guide

This guide explains the structured logging setup, how to add logs to new code, and how request IDs are threaded through the application.

---

## Overview

All logs are emitted as **JSON to stdout**, one record per line. This makes them directly consumable by log aggregation systems (ELK Stack, Datadog, AWS CloudWatch, Grafana Loki) without a parsing step.

The setup lives in `app/core/logging.py` and is initialized once at application startup via `configure_logging()`, called at the top of `create_app()` in `app/main.py`.

---

## Log Format

Every log line is a JSON object with the following fields:

| Field | Source | Example |
|-------|--------|---------|
| `asctime` | Timestamp (UTC) | `"2026-02-18T14:30:45Z"` |
| `name` | Logger name (`__name__` of the module) | `"app.services.server_service"` |
| `levelname` | Log level | `"INFO"` |
| `message` | Log message | `"Server created"` |
| `request_id` | Current request correlation ID | `"a1b2c3d4e5f6..."` or `"-"` |
| `service` | App name from settings | `"OpenStack VM Lifecycle API"` |
| `version` | App version from settings | `"0.1.0"` |
| `env` | Environment from settings | `"production"` |
| `...extra` | Custom fields passed via `extra={}` | `"server_id"`, `"flavor_id"`, etc. |

**Sample output:**
```json
{
  "asctime": "2026-02-18T14:30:45Z",
  "name": "app.services.server_service",
  "levelname": "INFO",
  "message": "Server created",
  "request_id": "a1b2c3d4e5f6abc",
  "service": "OpenStack VM Lifecycle API",
  "version": "0.1.0",
  "env": "production",
  "server_id": "5219cabe-2c70-4a49-b726-1c0bfdd7cb39",
  "server_name": "web-01",
  "flavor_id": "11111111-0000-0000-0000-000000000002",
  "status": "ACTIVE"
}
```

---

## Log Levels

| Level | When to use | Example |
|-------|------------|---------|
| `DEBUG` | Read operations, detailed internal flow. **Only emitted when `DEBUG=true`.** | Fetching a flavor by ID |
| `INFO` | Every mutating operation, state transitions, app startup/shutdown | Server created, state transition |
| `WARNING` | Invalid action attempted but handled gracefully | Invalid state transition attempt |
| `ERROR` | Unhandled exception, infrastructure failure. Always include `exc_info=True`. | Unexpected exception in handler |
| `CRITICAL` | Unrecoverable failure preventing startup | Database unreachable on boot |

---

## Request ID Correlation

Every request gets a unique correlation ID:

1. **`RequestIdMiddleware`** (`app/core/middleware.py`) runs first on every request
2. It checks for an `X-Request-ID` header from the caller; if absent, generates `uuid.uuid4().hex`
3. The ID is stored in:
   - `request.state.request_id` — accessible inside endpoint handlers
   - `request_id_var` ContextVar — automatically read by the logging filter
   - `X-Request-ID` response header — echoed back for client-side tracing
4. `_RequestIdFilter` reads `request_id_var` and injects the value into every log record

**Result:** All logs within a single request — from the HTTP layer down through services and infra — share the same `request_id`, making it trivial to filter logs for a single request in any log aggregation tool.

**Outside request context** (e.g., during startup, background tasks): `request_id` defaults to `"-"`.

**Client usage:**
```bash
curl -H "X-Request-ID: my-trace-123" http://localhost:8000/api/v1/servers
# All logs for this request will include: "request_id": "my-trace-123"
# Response will include: X-Request-ID: my-trace-123
```

---

## Adding Logs to New Code

### 1. Get a logger

At the top of any module:
```python
import logging

logger = logging.getLogger(__name__)
```

### 2. Log with context fields

Pass custom context via the `extra` parameter:
```python
logger.info("Server created", extra={
    "server_id": server.id,
    "server_name": server.name,   # NOT "name" — that's a reserved LogRecord field
    "flavor_id": server.flavor_id,
})

logger.warning("Invalid transition", extra={
    "server_id": server_id,
    "current_status": server.status.value,
    "action": payload.action,
})

logger.error("Unexpected failure", exc_info=True, extra={
    "server_id": server_id,
})
```

### 3. Reserved field names to avoid in `extra`

The following names are built-in `LogRecord` attributes and **cannot** be used as keys in `extra` — doing so raises a `KeyError` at runtime:

`name`, `msg`, `args`, `levelname`, `levelno`, `pathname`, `filename`, `module`, `exc_info`, `exc_text`, `lineno`, `funcName`, `created`, `msecs`, `thread`, `threadName`, `process`, `processName`, `message`

Use prefixed names instead: `server_name` instead of `name`, `error_msg` instead of `msg`, etc.

---

## Log Level Configuration

Controlled by the `DEBUG` environment variable:

| `DEBUG` value | Log level |
|--------------|-----------|
| `false` (default) | `INFO` and above |
| `true` | `DEBUG` and above (also enables SQLAlchemy query echo) |

Set in `.env`:
```
DEBUG=true   # development: verbose
DEBUG=false  # production: INFO and above only
```

Third-party loggers (`uvicorn.access`, `sqlalchemy.engine`) are suppressed to `WARNING` regardless of the `DEBUG` setting, to reduce noise.

---

## Exception Handler Logging

All three exception handlers in `app/core/exceptions.py` log before returning a response:

| Handler | Log level | exc_info |
|---------|-----------|----------|
| `AppException` (4xx) | `WARNING` | No |
| `AppException` (5xx) | `ERROR` | No |
| `RequestValidationError` (422) | `INFO` | No |
| Unhandled `Exception` (500) | `ERROR` | **Yes** — full stack trace |

The generic 500 handler is the most important: previously it returned a response without logging anything, making production failures completely invisible. It now logs the full traceback while still returning a safe `{"error": {"code": "INTERNAL_ERROR", ...}}` response to the client.

---

## What's Not Yet Implemented

See `docs/roadmap.md` for future observability work:

- **Prometheus metrics** — request latency histograms, error rate counters, active VM count
- **OpenTelemetry tracing** — distributed spans across service/infra/DB layers
- **Structured log library** — potential migration to `structlog` for richer context binding
