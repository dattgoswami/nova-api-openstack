# ADR 003 — OpenStack Abstraction Layer (ABC Pattern)

**Status:** Accepted
**Date:** 2026-02-17

## Context

We need to interact with OpenStack (Nova/Glance) for VM lifecycle operations but:
1. No real OpenStack cluster is available in development and CI
2. openstacksdk calls are synchronous (or require async wrappers)
3. We want to unit-test business logic without any external service dependency
4. We need a clear contract so a real implementation can be dropped in without touching service layer code

## Decision

Define `OpenStackClientBase` as an **Abstract Base Class (ABC)** with async method signatures mirroring the openstacksdk interface. Provide two implementations:
- `MockOpenStackClient` — delegates to the SQLAlchemy async DB (always available)
- `RealOpenStackClient` — skeleton with documented openstacksdk calls (production-ready skeleton)

Selection is controlled by `USE_MOCK_OPENSTACK` environment variable.

## Rationale

### Why an ABC and not duck typing?

The ABC makes the interface contract explicit and enforced. Any new implementation (e.g., a caching client, a multi-region client) must implement every method or get a clear `TypeError` at class definition time, not a mysterious `AttributeError` at runtime.

### Why delegate mock to the DB?

The mock client uses the same SQLAlchemy session as the request, so:
- State transitions are part of the same transaction (atomic)
- Tests can inspect DB state after API calls
- No in-memory dictionaries that diverge from the real schema

### Why not use `unittest.mock` in tests?

Mocking at the infra boundary (with `MagicMock`) would test that we called the right method with the right args — but not that the overall system works. Using the mock client gives us end-to-end confidence: we test through the full stack (HTTP → Service → Infra → DB) with real SQL queries.

### Migration path to real OpenStack

1. Install: `pip install openstacksdk`
2. Set `USE_MOCK_OPENSTACK=false` in `.env`
3. Set `OPENSTACK_AUTH_URL`, `OPENSTACK_USERNAME`, etc.
4. Implement the 9 methods in `RealOpenStackClient` using the `conn.compute.*` and `conn.image.*` calls documented in the skeleton comments

The service layer and HTTP layer are completely unchanged.

## Consequences

- **Positive:** Full end-to-end testing without OpenStack, zero mocking library dependency, clean migration path.
- **Negative:** Mock client must stay in sync with the real client interface — ABC enforcement helps here.
- **Neutral:** openstacksdk is synchronous; `RealOpenStackClient` will need `asyncio.to_thread` wrappers or the async openstack SDK if available.
