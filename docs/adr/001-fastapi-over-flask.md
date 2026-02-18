# ADR 001 — FastAPI over Flask

**Status:** Accepted
**Date:** 2026-02-17

## Context

We need a Python web framework for a REST API that manages VM lifecycle. The framework needs to handle async I/O efficiently (database and eventual OpenStack SDK calls), generate API documentation automatically, and provide strong request/response validation with minimal boilerplate.

## Decision

Use **FastAPI 0.115** with **Pydantic v2**.

## Rationale

| Criterion | FastAPI | Flask |
|-----------|---------|-------|
| Async-native | Yes (ASGI) | No (WSGI by default; async support is bolted on via Quart) |
| Auto OpenAPI docs | Built-in Swagger + ReDoc | Requires flask-restx or flasgger |
| Request validation | Pydantic v2 (native) | marshmallow or custom |
| Type safety | Full typing support | Partial |
| Dependency injection | Built-in | Manual or flask-injector |
| Performance | Comparable to Node.js | Slower under async load |

The async-native design is essential: each request will eventually invoke openstacksdk (network I/O), and with Flask we'd either block the event loop or need a complex thread-pool workaround. FastAPI's `async def` endpoints and SQLAlchemy async ORM compose naturally.

The built-in DI system (`Depends`) makes testing trivial — we override `get_db` and `get_openstack_client` in `conftest.py` without any mocking library.

## Consequences

- **Positive:** Free Swagger UI at `/docs`, type-safe request/response with Pydantic, async without greenlets.
- **Negative:** Slightly larger learning curve than Flask for developers unfamiliar with async Python. Pydantic v2 has some breaking changes from v1 that require care in model definitions.
- **Neutral:** Uvicorn as the ASGI server — mature, production-ready.
