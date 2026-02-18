"""
Tests for /api/v1/images — read-only image endpoints.
"""

from httpx import AsyncClient

from app.models.image import Image


class TestListImages:
    async def test_list_returns_seeded_images(self, client: AsyncClient, seed_images: list[Image]):
        resp = await client.get("/api/v1/images")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == len(seed_images)
        assert len(data["items"]) == len(seed_images)

    async def test_list_image_fields(self, client: AsyncClient, seed_images: list[Image]):
        resp = await client.get("/api/v1/images")
        item = resp.json()["items"][0]
        assert "id" in item
        assert "name" in item
        assert "os_distro" in item
        assert "min_disk_gb" in item
        assert "size_bytes" in item
        assert "status" in item

    async def test_list_pagination(self, client: AsyncClient, seed_images: list[Image]):
        resp = await client.get("/api/v1/images?limit=1&offset=0")
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["total"] == len(seed_images)
        assert data["next_offset"] == 1


class TestGetImage:
    async def test_get_existing_image(self, client: AsyncClient, image_id: str):
        resp = await client.get(f"/api/v1/images/{image_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == image_id

    async def test_get_nonexistent_returns_404(self, client: AsyncClient):
        resp = await client.get("/api/v1/images/nonexistent-id")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "IMAGE_NOT_FOUND"
