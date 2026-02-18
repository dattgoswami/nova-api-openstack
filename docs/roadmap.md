# Roadmap

Items below are out of scope for this POC but represent the natural next steps for a production-grade platform service.

---

## Authentication & Authorization

**Priority: P0 for production**

- Add **JWT bearer token** authentication via `python-jose` or `authlib`
- FastAPI OAuth2 dependency (`OAuth2PasswordBearer`) or API key header (`X-API-Key`)
- Role-based access control (RBAC): `admin` vs `viewer` roles
- Keystone token passthrough for real OpenStack environments — validate tokens against Keystone identity service

## Rate Limiting

- Per-IP and per-user rate limits using `slowapi` (Starlette/FastAPI middleware)
- Configurable limits per endpoint tier (e.g., POST endpoints limited more aggressively)
- Return `Retry-After` header on 429 responses

## Async Event System

VM operations in real OpenStack are asynchronous — `nova boot` returns immediately, and the VM transitions through BUILD → ACTIVE over seconds. Production handling:

- **WebSocket endpoint** (`/api/v1/servers/{id}/events`) for real-time status updates
- Or **polling pattern** with `GET /api/v1/servers/{id}` and an `ETag`/`If-None-Match` header
- Background task queue (Celery + Redis, or Python `asyncio.create_task`) to poll OpenStack for status transitions and update the DB

## Database

- **Migrate to PostgreSQL** — change `DATABASE_URL` to `postgresql+asyncpg://...`, nothing else
- Add **Alembic** for schema migrations (`alembic init migrations`, `alembic revision --autogenerate`)
- Connection pooling via `asyncpg` pool settings in `create_async_engine`
- Database health check in `/health` endpoint

## Observability

### Metrics
- Expose **Prometheus** metrics via `prometheus-fastapi-instrumentator`
- Key metrics: request latency histogram, error rate by endpoint, active VM count, state transition counts

### Tracing
- **OpenTelemetry** instrumentation for distributed tracing
- Trace context propagation through service → infra → DB layers

### Structured Logging ✅ Implemented
- JSON-structured log output via `python-json-logger` — see `docs/logging.md`
- Request ID middleware (`app/core/middleware.py`) threads correlation IDs through all log lines automatically via `ContextVar`
- Remaining: Prometheus metrics, OpenTelemetry tracing, `structlog` migration (optional)

## Multi-Region Support

- Extend `OpenStackClientBase` with a `region` parameter
- `RegionRouter` service that dispatches to region-specific clients
- `GET /api/v1/regions` endpoint to list available regions

## Caching

- Redis cache layer in front of flavor and image listings (these change rarely)
- `Cache-Control` and `ETag` headers for GET responses

## Quota Management

- Track per-project resource usage (vCPU count, RAM, disk)
- Enforce quotas before VM creation
- `GET /api/v1/quotas` endpoint

## CI/CD Enhancements

- Pre-commit hooks for ruff + mypy
- Integration test stage against a real OpenStack sandbox (DevStack)
- Automated Docker image publishing to GHCR on merge to `main`
- Semantic versioning + changelog automation

## API Versioning

- Current: `/api/v1/`
- Future: maintain v1 during v2 development period, deprecate with `Sunset` header
- OpenAPI spec versioning to track schema evolution

## Server Console / VNC

- `POST /api/v1/servers/{id}/console` — return VNC/SPICE console URL
- Maps to `nova get-vnc-console` in openstacksdk
