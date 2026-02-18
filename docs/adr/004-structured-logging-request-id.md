# ADR 004 — Structured JSON Logging & Request ID Middleware

**Status:** Accepted
**Date:** 2026-02-18

---

## Context

In production, debugging distributed issues requires:

1. **Request tracing** — the ability to correlate all log lines produced by a single user request across every layer (HTTP → Service → Infra → DB)
2. **Structured, machine-readable logs** — plain text logs cannot be efficiently indexed, searched, or alerted on at scale
3. **Zero-friction instrumentation** — developers should not need to thread a request ID through every function signature manually; it should propagate automatically

The original codebase had zero logging, meaning production failures were completely silent from an observability standpoint.

---

## Decision

Implement structured JSON logging with automatic request ID injection using the Python standard `logging` module and `python-json-logger`:

- **`app/core/logging.py`** — `configure_logging()` sets up a JSON formatter, a `ContextVar`-backed filter, and service metadata enrichment
- **`app/core/middleware.py`** — `RequestIdMiddleware` extracts or generates a correlation ID per request and stores it in a `ContextVar`

---

## Rationale

### Why JSON logs?

JSON is the de facto format for structured log ingestion:
- ELK, Splunk, Datadog, CloudWatch Logs Insights all parse JSON natively
- Fields like `request_id`, `server_id`, and `error_code` become filterable dimensions
- No regex parsing required — operations teams can immediately query logs

### Why `python-json-logger` over `structlog` or `loguru`?

`python-json-logger` wraps the standard `logging` module with a drop-in JSON formatter. This means:
- Existing `logging.getLogger(__name__)` calls work unchanged throughout the codebase
- Third-party libraries that use `logging` automatically emit JSON too
- Minimal dependency surface — one small library, no paradigm shift
- `structlog` and `loguru` require replacing all logger instantiation patterns, which is a larger migration

### Why `ContextVar` over passing `request_id` as a parameter?

Python's `threading.local()` does not work with asyncio — multiple coroutines run on the same thread. `ContextVar` is the asyncio-safe equivalent:
- Each task (request) gets its own isolated context
- The value propagates automatically to child coroutines
- Middleware sets it once; all downstream code reads it implicitly
- No function signatures need to change

### Why a middleware rather than a FastAPI dependency?

Middleware runs unconditionally for every request, including requests that hit 404 or bypass routing entirely. A FastAPI `Depends()` only runs for matched routes. The middleware guarantees that even error responses include an `X-Request-ID` header and that all exception handler logs carry a `request_id`.

---

## Consequences

**Positive:**
- All logs include `request_id`, enabling instant per-request log filtering in any aggregation tool
- The generic 500 exception handler now logs the full stack trace — production failures are no longer silent
- Adding context to logs is a one-liner: `logger.info("...", extra={"server_id": id})`
- Clients can pass their own trace ID via `X-Request-ID` for end-to-end tracing across services

**Negative:**
- Adds `python-json-logger` as a runtime dependency (very small, actively maintained)
- Developers must avoid reserved `LogRecord` attribute names in `extra` dicts (see `docs/logging.md`)
- Log output is no longer human-readable without a JSON formatter (`jq`, Kibana, etc.)

**Neutral:**
- Log level is still controlled by `DEBUG` env var; behaviour is backward-compatible
- The standard `logging` module interface is unchanged — any code using `logging.getLogger()` works as before

---

## Implementation Notes

- `configure_logging()` must be called before any module instantiates a logger — it is the first call in `create_app()` in `app/main.py`
- `RequestIdMiddleware` is added before `register_exception_handlers()` so exception handlers also have access to `request_id_var`
- Outside request context (startup, background tasks), `request_id` defaults to `"-"` — see `request_id_var` declaration in `app/core/logging.py`
- See `docs/logging.md` for usage patterns, reserved field names, and future observability roadmap
