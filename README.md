# OpenStack VM Lifecycle API

A REST API for managing OpenStack VM lifecycle operations, built with **FastAPI**, **SQLAlchemy async**, and **Pydantic v2**. The OpenStack layer is abstracted behind an interface with a mock implementation backed by SQLite — no real cluster needed.

> **Production Readiness Notice**
> This is a proof-of-concept demonstrating architecture and engineering practices. It is **not yet production-ready**. Missing before any live deployment: authentication/authorization, rate limiting, database migrations (Alembic), PostgreSQL, and a CI/CD deployment pipeline. See [docs/roadmap.md](docs/roadmap.md) for the full list.

---

## Quick Start

### Local Development

```bash
# 1. Clone and enter the project
git clone https://github.com/dattgoswami/nova-api-openstack.git
cd nova-api-openstack

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Copy and configure environment
cp .env.example .env

# 5. Start the API
uvicorn app.main:app --reload
```

Visit [http://localhost:8000/docs](http://localhost:8000/docs) for the interactive Swagger UI.

### Docker

```bash
docker-compose up --build
```

API available at [http://localhost:8000](http://localhost:8000).

---

## API Reference

### Health Check

```
GET /health
```

### Servers (VM Lifecycle)

| Method | Path | Description | Status |
|--------|------|-------------|--------|
| POST | `/api/v1/servers` | Boot a new VM | 201 |
| GET | `/api/v1/servers` | List VMs (paginated) | 200 |
| GET | `/api/v1/servers/{id}` | Get a VM | 200 |
| PATCH | `/api/v1/servers/{id}` | Rename/update metadata | 200 |
| DELETE | `/api/v1/servers/{id}` | Terminate VM | 204 |
| POST | `/api/v1/servers/{id}/action` | Lifecycle action | 202 |

### Flavors (Read-only)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/flavors` | List flavors (paginated) |
| GET | `/api/v1/flavors/{id}` | Get a flavor |

### Images (Read-only)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/images` | List images (paginated) |
| GET | `/api/v1/images/{id}` | Get an image |

### Seed Data Reference

The following UUIDs are pre-seeded on every fresh startup and are stable across restarts:

**Flavors**

| Name | UUID |
|------|------|
| m1.tiny (1 vCPU, 512 MB, 1 GB) | `11111111-0000-0000-0000-000000000001` |
| m1.small (1 vCPU, 2 GB, 20 GB) | `11111111-0000-0000-0000-000000000002` |
| m1.medium (2 vCPU, 4 GB, 40 GB) | `11111111-0000-0000-0000-000000000003` |
| m1.large (4 vCPU, 8 GB, 80 GB) | `11111111-0000-0000-0000-000000000004` |
| m1.xlarge (8 vCPU, 16 GB, 160 GB) | `11111111-0000-0000-0000-000000000005` |

**Images**

| Name | UUID |
|------|------|
| Ubuntu 22.04 LTS | `22222222-0000-0000-0000-000000000001` |
| Debian 12 | `22222222-0000-0000-0000-000000000002` |
| CentOS Stream 9 | `22222222-0000-0000-0000-000000000003` |
| Fedora 39 | `22222222-0000-0000-0000-000000000004` |

### Request/Response Examples

**Create a server (using seed UUIDs — no lookup required):**
```bash
curl -X POST http://localhost:8000/api/v1/servers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "web-01",
    "flavor_id": "11111111-0000-0000-0000-000000000002",
    "image_id": "22222222-0000-0000-0000-000000000001"
  }'
```

**Perform an action:**
```bash
# Stop
curl -X POST http://localhost:8000/api/v1/servers/<id>/action \
  -H "Content-Type: application/json" \
  -d '{"action": "stop"}'

# Resize to a larger flavor
curl -X POST http://localhost:8000/api/v1/servers/<id>/action \
  -H "Content-Type: application/json" \
  -d '{"action": "resize", "flavor_id": "11111111-0000-0000-0000-000000000004"}'
```

**List servers (paginated):**
```bash
curl "http://localhost:8000/api/v1/servers?limit=20&offset=0"
```

**Pagination limits:** `limit` accepts 1–100 (default 20). `offset` must be ≥ 0 (default 0). No rate limiting is currently enforced — see [docs/roadmap.md](docs/roadmap.md).

### VM State Machine

```
              CREATE
                ↓
             [ACTIVE]  ──stop──→  [SHUTOFF]
               ↑  ↑                   |
            reboot  └────start────────┘
               ↓
            [ACTIVE]

           resize→ [ACTIVE] (new flavor applied)

Any state ──delete──→ [DELETED]
```

Invalid transitions return **409 Conflict**.

### Error Envelope

All errors use a consistent envelope:
```json
{
  "error": {
    "code": "SERVER_NOT_FOUND",
    "message": "Server abc123 not found",
    "details": null
  }
}
```

### Pagination Response

```json
{
  "items": [...],
  "total": 42,
  "limit": 20,
  "offset": 0,
  "next_offset": 20
}
```

---

## Development

### Running Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=app --cov-report=term-missing

# Specific test file
pytest tests/api/test_servers.py -v
```

### Lint & Format

```bash
# Check linting
ruff check .

# Format code
ruff format .

# Check formatting (CI mode)
ruff format --check .
```

### Type Checking

```bash
mypy app/
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./intuitive.db` | Database connection string. Change to `postgresql+asyncpg://...` for production |
| `ENV` | `development` | Environment label (appears in logs and health check response) |
| `DEBUG` | `false` | Set to `true` to emit `DEBUG`-level logs and enable SQLAlchemy query echo |
| `USE_MOCK_OPENSTACK` | `true` | `true` uses the SQLite-backed mock client; `false` uses `RealOpenStackClient` (requires OpenStack credentials) |
| `OPENSTACK_AUTH_URL` | `` | Keystone endpoint — only needed when `USE_MOCK_OPENSTACK=false` |
| `OPENSTACK_USERNAME` | `` | OpenStack username — only needed when `USE_MOCK_OPENSTACK=false` |
| `OPENSTACK_PASSWORD` | `` | OpenStack password (`SecretStr` — masked in logs) — only needed when `USE_MOCK_OPENSTACK=false` |
| `OPENSTACK_PROJECT_NAME` | `` | OpenStack project — only needed when `USE_MOCK_OPENSTACK=false` |
| `OPENSTACK_REGION` | `RegionOne` | OpenStack region — only needed when `USE_MOCK_OPENSTACK=false` |

---

## Architecture

See [docs/architecture.md](docs/architecture.md) for the full design writeup, [docs/logging.md](docs/logging.md) for the structured logging guide, and [docs/adr/](docs/adr/) for Architecture Decision Records.

### Layer Overview

```
HTTP Layer      (app/api/v1/)          FastAPI routers + request/response
     ↓
Service Layer   (app/services/)        Business logic + state machine
     ↓
Infra Layer     (app/infra/openstack/) Abstract client (mock or real)
     ↓
DB Layer        (app/db/ + app/models/) SQLAlchemy async ORM
```

### Key Design Decisions

- **FastAPI** — async-native, auto OpenAPI docs, Pydantic v2 integration
- **SQLAlchemy async** — non-blocking ORM, trivially swappable to Postgres
- **OpenStack abstraction** — `MockOpenStackClient` for dev/test, `RealOpenStackClient` skeleton for production
- **State machine** — enforced in service layer before any infra call
- **Error envelope** — consistent `{"error": {"code", "message", "details"}}` across all error cases

---

## Project Structure

```
intuitive/
├── app/
│   ├── main.py                    # FastAPI app factory + lifespan + health check
│   ├── config.py                  # pydantic-settings (all env vars)
│   ├── dependencies.py            # Dependency injection wiring
│   ├── api/v1/endpoints/          # HTTP layer (servers, flavors, images)
│   ├── core/
│   │   ├── exceptions.py          # Custom exception classes + handlers
│   │   ├── logging.py             # Structured JSON logging setup + request_id ContextVar
│   │   ├── middleware.py          # RequestIdMiddleware (X-Request-ID propagation)
│   │   └── pagination.py          # PaginationParams + PaginatedResponse[T]
│   ├── db/                        # Async SQLAlchemy engine + session
│   ├── models/                    # ORM models (Server, Flavor, Image)
│   ├── schemas/                   # Pydantic v2 request/response schemas
│   ├── services/                  # Business logic + state machine
│   └── infra/openstack/           # OpenStack client abstraction (mock + real skeleton)
├── tests/
│   ├── api/                       # HTTP endpoint tests (in-memory SQLite)
│   └── services/                  # State machine unit tests
├── docs/
│   ├── architecture.md            # Full design writeup
│   ├── logging.md                 # Structured logging guide
│   ├── roadmap.md                 # Future work
│   └── adr/                       # Architecture Decision Records
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

---

## Smoke Test (Manual)

Copy-paste ready — seed UUIDs are stable so no discovery step is needed.

```bash
# Start the API
uvicorn app.main:app --reload

# Verify health (should return {"status":"healthy",...})
curl http://localhost:8000/health

# Create a server
SERVER=$(curl -s -X POST http://localhost:8000/api/v1/servers \
  -H "Content-Type: application/json" \
  -d '{"name":"test-vm","flavor_id":"11111111-0000-0000-0000-000000000002","image_id":"22222222-0000-0000-0000-000000000001"}')
ID=$(echo $SERVER | jq -r '.id')
echo "Created server: $ID"

# Stop it (ACTIVE → SHUTOFF)
curl -s -X POST "http://localhost:8000/api/v1/servers/$ID/action" \
  -H "Content-Type: application/json" -d '{"action":"stop"}' | jq '.status'

# Try to stop again — expect 409 INVALID_STATE_TRANSITION
curl -s -X POST "http://localhost:8000/api/v1/servers/$ID/action" \
  -H "Content-Type: application/json" -d '{"action":"stop"}' | jq '.error.code'

# Start it back up (SHUTOFF → ACTIVE)
curl -s -X POST "http://localhost:8000/api/v1/servers/$ID/action" \
  -H "Content-Type: application/json" -d '{"action":"start"}' | jq '.status'

# Delete it (expect HTTP 204 — no body)
curl -s -o /dev/null -w "%{http_code}" -X DELETE "http://localhost:8000/api/v1/servers/$ID"

# Confirm 404 after deletion
curl -s "http://localhost:8000/api/v1/servers/$ID" | jq '.error.code'
```

Expected final output: `"SERVER_NOT_FOUND"`

---

## Operations

### Checking logs

All logs are JSON on stdout. Filter by request ID, server, or error code:

```bash
# Follow live logs and pretty-print
uvicorn app.main:app --reload 2>&1 | jq .

# Filter all logs for a specific request
cat app.log | jq 'select(.request_id == "abc123")'

# Find all server creation events
cat app.log | jq 'select(.message == "Server created")'

# Find all unhandled 500 errors
cat app.log | jq 'select(.levelname == "ERROR")'

# Find all invalid state transition attempts
cat app.log | jq 'select(.message == "Invalid state transition attempt")'
```

### When the health check fails

`GET /health` returns HTTP 503 when the database is unreachable.

**Debugging steps:**

```bash
# 1. Check the database file exists (SQLite dev mode)
ls -lh intuitive.db

# 2. Check recent error logs
cat app.log | jq 'select(.levelname == "ERROR")' | tail -20

# 3. Reset the database (⚠️ destroys all data — dev only)
rm intuitive.db
# Restart the server — tables and seed data are recreated automatically on startup

# 4. For Docker: check the volume mount
docker volume inspect intuitive_db_data
```

### Switching from mock to real OpenStack

The `USE_MOCK_OPENSTACK` env var controls which client is used (see `app/dependencies.py`):

1. Set credentials in `.env`:
   ```
   USE_MOCK_OPENSTACK=false
   OPENSTACK_AUTH_URL=https://identity.example.com:5000/v3
   OPENSTACK_USERNAME=your-user
   OPENSTACK_PASSWORD=your-password
   OPENSTACK_PROJECT_NAME=your-project
   OPENSTACK_REGION=RegionOne
   ```
2. Implement the methods in `app/infra/openstack/real_client.py` (each method has comments showing the correct openstacksdk call)
3. Validate locally: `curl http://localhost:8000/api/v1/flavors` — should return flavors from the real cluster
4. The mock and real clients share the same interface (`OpenStackClientBase`), so all existing tests still pass

### Database backup and restore

**SQLite (development):**
```bash
# Backup
cp intuitive.db intuitive.db.backup

# Restore
cp intuitive.db.backup intuitive.db
```

**PostgreSQL (production):** Switch `DATABASE_URL` to `postgresql+asyncpg://...`, add Alembic for migrations, and use `pg_dump`/`pg_restore`. See [docs/roadmap.md](docs/roadmap.md) for the migration plan.

### Rotating OpenStack credentials

1. Update the value in your secrets manager (Vault, AWS Secrets Manager, Kubernetes Secret)
2. Update the `OPENSTACK_PASSWORD` environment variable in your deployment
3. Restart the service — `pydantic-settings` reads env vars at startup, not at request time
4. Verify with `GET /health` — if the health check passes, the new credentials are working

### Common startup issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Address already in use` on port 8000 | Another process is using the port | `lsof -i :8000` then kill the PID, or use `--port 8001` |
| `ModuleNotFoundError: No module named 'app'` | Running uvicorn from wrong directory | Run from the project root (`cd intuitive`) |
| `sqlalchemy.exc.OperationalError: no such table` | DB file exists but tables are missing | Delete `intuitive.db` and restart — `create_all` runs on every startup |
| Tests hang indefinitely | `asyncio_mode` misconfiguration | Confirm `asyncio_mode = "auto"` is set in `pyproject.toml` |
