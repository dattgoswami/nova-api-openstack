# Architecture

## Overview

The API is structured in four distinct layers, each with a single responsibility and a clear interface boundary. Dependencies only flow downward — HTTP → Service → Infra → DB.

```
┌─────────────────────────────────────────┐
│  HTTP Layer  (app/api/v1/)              │
│  FastAPI routers, request validation,   │
│  response serialization                 │
└────────────────────┬────────────────────┘
                     │ calls
┌────────────────────▼────────────────────┐
│  Service Layer  (app/services/)         │
│  Business logic, state machine,         │
│  cross-cutting validation               │
└────────────────────┬────────────────────┘
                     │ calls
┌────────────────────▼────────────────────┐
│  Infra Layer  (app/infra/openstack/)    │
│  OpenStackClientBase ABC,               │
│  MockOpenStackClient / RealClient       │
└────────────────────┬────────────────────┘
                     │ reads/writes
┌────────────────────▼────────────────────┐
│  DB Layer  (app/db/ + app/models/)      │
│  SQLAlchemy async ORM, aiosqlite        │
└─────────────────────────────────────────┘
```

---

## Layer Details

### HTTP Layer (`app/api/v1/`)

- **Pure request/response translation.** No business logic lives here.
- FastAPI routers validate inputs via Pydantic v2 schemas before the handler body runs.
- Response schemas are independent of ORM models — the endpoint helpers convert `*Record` dataclasses (from the infra layer) into Pydantic response objects.
- HTTP status codes are explicit and intentional: 201 (created), 202 (async action accepted), 204 (deleted), 404, 409, 422, 500.

### Service Layer (`app/services/`)

- Enforces the **VM state machine** before any infra call. This keeps transition logic out of both the HTTP layer (too thin) and the infra layer (too coupled to storage).
- Validates cross-resource constraints (e.g., flavor exists before create/resize).
- Raises typed domain exceptions (`ServerNotFoundError`, `InvalidStateTransitionError`, etc.) that are translated to HTTP responses by exception handlers registered in `app/core/exceptions.py`.
- Services are thin — they compose infra calls, not reimplement them.

### Infra Layer (`app/infra/openstack/`)

- `OpenStackClientBase` is an **Abstract Base Class** that mirrors the openstacksdk interface surface. This decouples the service layer from the storage implementation entirely.
- `MockOpenStackClient` implements the ABC against SQLAlchemy, enabling end-to-end testing without a real cluster and providing a working development environment.
- `RealOpenStackClient` provides a documented skeleton for wiring openstacksdk — it raises `NotImplementedError` with clear comments showing which SDK calls to make.
- Switching from mock to real is a single env var change (`USE_MOCK_OPENSTACK=false`) plus implementing the real client methods.

### DB Layer (`app/db/`, `app/models/`)

- SQLAlchemy 2.0 async ORM with `aiosqlite` driver.
- All queries go through the ORM — no raw SQL, preventing SQL injection by construction.
- The `AsyncSession` is scoped per-request via FastAPI's dependency injection (`get_db`). The session commits on success and rolls back on exception.
- SQLite is used for local development; switching to Postgres requires only changing `DATABASE_URL` (e.g., `postgresql+asyncpg://...`).

---

## State Machine

The VM lifecycle state machine is defined in `app/services/server_service.py`:

```python
VALID_TRANSITIONS = {
    ServerStatus.ACTIVE:   {"stop": SHUTOFF, "reboot": ACTIVE, "resize": ACTIVE},
    ServerStatus.SHUTOFF:  {"start": ACTIVE},
    ServerStatus.BUILD:    {},   # system-managed
    ServerStatus.REBOOT:   {},   # system-managed
    ServerStatus.RESIZE:   {},   # system-managed
    ServerStatus.VERIFY_RESIZE: {"confirm_resize": ACTIVE},
}
```

Any action not in the allowed set for the current state raises `InvalidStateTransitionError` (409 Conflict). The mock client applies state transitions atomically in the same DB transaction.

---

## Error Handling

All errors use a consistent JSON envelope:

```json
{"error": {"code": "SERVER_NOT_FOUND", "message": "...", "details": null}}
```

Exception handlers are registered in `app/core/exceptions.py` and convert:
- `AppException` subclasses → their declared `status_code` and `error_code`
- `RequestValidationError` (Pydantic) → 422 with field-level details
- Unhandled `Exception` → 500 with no internal details leaked

---

## Dependency Injection

FastAPI's DI chain for a server endpoint request:

```
Request
  → get_db()               # yields AsyncSession
  → get_openstack_client() # wraps session in MockOpenStackClient
  → get_server_service()   # wraps client in ServerService
  → endpoint handler       # calls service methods
```

In tests, `get_db` and `get_openstack_client` are overridden via `dependency_overrides` in `tests/conftest.py`:

```python
app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_openstack_client] = override_get_openstack_client
```

Each test gets a **function-scoped in-memory SQLite database** (`sqlite+aiosqlite:///:memory:`), so state never leaks between tests. The `seed_flavors` and `seed_images` fixtures populate the test DB before each test, and the entire DB is discarded afterward. No mocking library is used — the full stack (HTTP → Service → Infra → ORM) runs in-process, giving integration-level confidence with unit-test isolation speed.

---

## Data Models

### Server
| Field | Type | Notes |
|-------|------|-------|
| id | UUID string | Primary key |
| name | string(255) | User-specified |
| status | enum | ServerStatus |
| flavor_id | FK → flavors | Hardware profile |
| image_id | FK → images | OS image |
| ip_address | string(45) | Assigned on creation |
| created_at | datetime | Immutable |
| updated_at | datetime | Updated on change |

### Flavor (read-only, seeded)
| Field | Type |
|-------|------|
| id | UUID string |
| name | string |
| vcpus | int |
| ram_mb | int |
| disk_gb | int |

### Image (read-only, seeded)
| Field | Type |
|-------|------|
| id | UUID string |
| name | string |
| os_distro | string |
| min_disk_gb | int |
| size_bytes | bigint |
| status | string |

---

## Structured Logging & Request Correlation

All application logs are emitted as JSON, enabling log aggregation systems (ELK, Datadog, CloudWatch) to index and query them without parsing.

### Setup

`configure_logging()` is called once at the start of `create_app()` in `app/main.py`. It configures:
- A JSON formatter (`python-json-logger`) that emits each record as a single JSON line
- A `_RequestIdFilter` that reads from a `ContextVar` and injects `request_id` into every log record automatically
- Service metadata fields (`service`, `version`, `env`) appended to every record

### Request ID Propagation

`RequestIdMiddleware` (registered in `create_app()` before exception handlers) performs three steps per request:
1. Extracts `X-Request-ID` from the incoming header, or generates a UUID4 hex string
2. Stores the ID in `request.state.request_id` and sets `request_id_var` (a `ContextVar`)
3. Echoes the ID back in the `X-Request-ID` response header

Because the ContextVar is set at the outermost async boundary, all downstream code — service methods, infra calls, DB queries — automatically picks up the same `request_id` in their log records without any parameter threading.

### Sample log line

```json
{
  "asctime": "2026-02-18T14:30:45Z",
  "name": "app.services.server_service",
  "levelname": "INFO",
  "message": "Server created",
  "request_id": "a1b2c3d4e5f6...",
  "service": "OpenStack VM Lifecycle API",
  "version": "0.1.0",
  "env": "development",
  "server_id": "uuid...",
  "server_name": "web-01",
  "status": "ACTIVE"
}
```

### Log level conventions

| Level | When to use |
|-------|------------|
| `DEBUG` | Read operations, detailed flow (only emitted when `DEBUG=true`) |
| `INFO` | Every mutating operation, state transitions, startup/shutdown events |
| `WARNING` | Invalid state transition attempts, recoverable unexpected conditions |
| `ERROR` | Unhandled exceptions (always with `exc_info=True`), rollbacks, infra failures |
| `CRITICAL` | Unrecoverable startup failures |

### Exception handler logging

All three handlers in `app/core/exceptions.py` log before returning:
- `AppException` → `WARNING` for 4xx, `ERROR` for 5xx
- `RequestValidationError` → `INFO`
- Unhandled `Exception` → `ERROR` with full `exc_info=True` stack trace

---

## Health Check

`GET /health` performs a **deep check** rather than always returning `ok`:

1. Executes `SELECT 1` against the database via a fresh `AsyncSessionLocal` session
2. Returns HTTP **200** with `"status": "healthy"` if the query succeeds
3. Returns HTTP **503** with `"status": "unhealthy"` if the DB is unreachable

Response payload:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "env": "development",
  "uptime_s": 3812,
  "checks": { "database": { "status": "healthy" } }
}
```

This makes the endpoint suitable for Kubernetes readiness probes and load balancer health checks.

---

## Security Practices

- **No secrets in code** — all config via environment variables (pydantic-settings)
- **`SecretStr` for passwords** — `openstack_password` in `app/config.py` uses Pydantic's `SecretStr` type; the value is masked as `**********` in all repr and log output, preventing accidental credential leakage
- **Input validation at the boundary** — Pydantic v2 validates all request bodies and query params before handlers run
- **No raw SQL** — ORM-only queries prevent SQL injection
- **No stack traces in error responses** — the generic exception handler returns a safe 500 without internal details (stack traces go to structured logs only)
- **Non-root Docker user** — the runtime container runs as a dedicated `app` user
- **`.env` in `.gitignore`**, `.env.example` committed
