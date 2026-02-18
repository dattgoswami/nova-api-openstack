"""
Tests for /api/v1/flavors — read-only flavor endpoints.
"""

from httpx import AsyncClient

from app.models.flavor import Flavor


class TestListFlavors:
    async def test_list_returns_seeded_flavors(
        self, client: AsyncClient, seed_flavors: list[Flavor]
    ):
        resp = await client.get("/api/v1/flavors")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == len(seed_flavors)
        assert len(data["items"]) == len(seed_flavors)

    async def test_list_flavor_fields(self, client: AsyncClient, seed_flavors: list[Flavor]):
        resp = await client.get("/api/v1/flavors")
        item = resp.json()["items"][0]
        assert "id" in item
        assert "name" in item
        assert "vcpus" in item
        assert "ram_mb" in item
        assert "disk_gb" in item

    async def test_list_pagination(self, client: AsyncClient, seed_flavors: list[Flavor]):
        resp = await client.get("/api/v1/flavors?limit=1&offset=0")
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["total"] == len(seed_flavors)
        assert data["next_offset"] == 1


class TestGetFlavor:
    async def test_get_existing_flavor(self, client: AsyncClient, flavor_id: str):
        resp = await client.get(f"/api/v1/flavors/{flavor_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == flavor_id

    async def test_get_nonexistent_returns_404(self, client: AsyncClient):
        resp = await client.get("/api/v1/flavors/nonexistent-id")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "FLAVOR_NOT_FOUND"
