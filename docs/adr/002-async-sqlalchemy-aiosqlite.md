# ADR 002 — Async SQLAlchemy + aiosqlite

**Status:** Accepted
**Date:** 2026-02-17

## Context

We need a data persistence layer that:
1. Works asynchronously with FastAPI's ASGI event loop
2. Supports SQLite for local development (zero-dependency setup)
3. Can be swapped to PostgreSQL for production without code changes
4. Prevents SQL injection

## Decision

Use **SQLAlchemy 2.0 async** with **aiosqlite** driver for development/test, designed to swap to `asyncpg` + PostgreSQL in production.

## Rationale

SQLAlchemy 2.0 introduced first-class async support via `create_async_engine` and `AsyncSession`. Combined with the ORM's query interface, this gives us:

- **Non-blocking I/O:** All DB queries are awaitable and don't block the event loop.
- **ORM-only queries:** No raw SQL anywhere in the codebase, preventing SQL injection by construction.
- **Database portability:** Changing `DATABASE_URL` from `sqlite+aiosqlite://` to `postgresql+asyncpg://` requires zero application code changes.
- **Session-per-request scoping:** FastAPI's DI system (`get_db`) ensures each request gets a fresh session that auto-commits on success and auto-rolls-back on exception.

### Why SQLite for development?

SQLite requires zero infrastructure — no Docker container, no port, no configuration. Any developer can clone the repo and start the API immediately. For the mock OpenStack client, SQLite is also the backing store, so tests run entirely in-memory (`sqlite+aiosqlite:///:memory:`) with no cleanup required.

### Production path to PostgreSQL

```python
# .env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname

# That's the only change needed.
```

## Consequences

- **Positive:** Zero-config local development, async-safe, SQL injection prevented by ORM.
- **Negative:** SQLite has limitations (no `ALTER COLUMN`, limited concurrent writers) — not suitable for production under load.
- **Neutral:** aiosqlite has `check_same_thread=False` required in connect_args; this is safe in async mode since SQLAlchemy manages connection lifecycle.
