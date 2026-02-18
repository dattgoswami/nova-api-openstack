"""
Tests for /api/v1/servers — CRUD operations.
"""

from httpx import AsyncClient


async def create_test_server(
    client: AsyncClient, flavor_id: str, image_id: str, name: str = "test-server"
) -> dict:
    response = await client.post(
        "/api/v1/servers",
        json={"name": name, "flavor_id": flavor_id, "image_id": image_id},
    )
    assert response.status_code == 201, response.text
    return response.json()


class TestCreateServer:
    async def test_create_returns_201(self, client: AsyncClient, flavor_id: str, image_id: str):
        resp = await client.post(
            "/api/v1/servers",
            json={"name": "web-01", "flavor_id": flavor_id, "image_id": image_id},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "web-01"
        assert data["status"] == "ACTIVE"
        assert data["flavor_id"] == flavor_id
        assert data["image_id"] == image_id
        assert "id" in data
        assert "ip_address" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_invalid_flavor_returns_404(self, client: AsyncClient, image_id: str):
        resp = await client.post(
            "/api/v1/servers",
            json={"name": "web-01", "flavor_id": "nonexistent-id", "image_id": image_id},
        )
        assert resp.status_code == 404
        data = resp.json()
        assert data["error"]["code"] == "FLAVOR_NOT_FOUND"

    async def test_create_invalid_image_returns_404(self, client: AsyncClient, flavor_id: str):
        resp = await client.post(
            "/api/v1/servers",
            json={"name": "web-01", "flavor_id": flavor_id, "image_id": "nonexistent-id"},
        )
        assert resp.status_code == 404
        data = resp.json()
        assert data["error"]["code"] == "IMAGE_NOT_FOUND"

    async def test_create_missing_name_returns_422(
        self, client: AsyncClient, flavor_id: str, image_id: str
    ):
        resp = await client.post(
            "/api/v1/servers",
            json={"flavor_id": flavor_id, "image_id": image_id},
        )
        assert resp.status_code == 422

    async def test_create_empty_name_returns_422(
        self, client: AsyncClient, flavor_id: str, image_id: str
    ):
        resp = await client.post(
            "/api/v1/servers",
            json={"name": "", "flavor_id": flavor_id, "image_id": image_id},
        )
        assert resp.status_code == 422


class TestListServers:
    async def test_list_empty_returns_empty(self, client: AsyncClient):
        resp = await client.get("/api/v1/servers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["limit"] == 20
        assert data["offset"] == 0
        assert data["next_offset"] is None

    async def test_list_returns_created_server(
        self, client: AsyncClient, flavor_id: str, image_id: str
    ):
        await create_test_server(client, flavor_id, image_id)
        resp = await client.get("/api/v1/servers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "test-server"

    async def test_list_pagination(self, client: AsyncClient, flavor_id: str, image_id: str):
        for i in range(5):
            await create_test_server(client, flavor_id, image_id, name=f"server-{i}")

        resp = await client.get("/api/v1/servers?limit=2&offset=0")
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["next_offset"] == 2

        resp2 = await client.get("/api/v1/servers?limit=2&offset=4")
        data2 = resp2.json()
        assert len(data2["items"]) == 1
        assert data2["next_offset"] is None

    async def test_list_excludes_deleted(self, client: AsyncClient, flavor_id: str, image_id: str):
        server = await create_test_server(client, flavor_id, image_id)
        server_id = server["id"]
        await client.delete(f"/api/v1/servers/{server_id}")

        resp = await client.get("/api/v1/servers")
        data = resp.json()
        assert data["total"] == 0

    async def test_list_invalid_limit_returns_422(self, client: AsyncClient):
        resp = await client.get("/api/v1/servers?limit=0")
        assert resp.status_code == 422

    async def test_list_limit_over_max_returns_422(self, client: AsyncClient):
        resp = await client.get("/api/v1/servers?limit=101")
        assert resp.status_code == 422


class TestGetServer:
    async def test_get_existing_returns_200(
        self, client: AsyncClient, flavor_id: str, image_id: str
    ):
        created = await create_test_server(client, flavor_id, image_id)
        resp = await client.get(f"/api/v1/servers/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    async def test_get_nonexistent_returns_404(self, client: AsyncClient):
        resp = await client.get("/api/v1/servers/nonexistent-id")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "SERVER_NOT_FOUND"

    async def test_get_deleted_returns_404(
        self, client: AsyncClient, flavor_id: str, image_id: str
    ):
        server = await create_test_server(client, flavor_id, image_id)
        server_id = server["id"]
        await client.delete(f"/api/v1/servers/{server_id}")

        resp = await client.get(f"/api/v1/servers/{server_id}")
        assert resp.status_code == 404


class TestUpdateServer:
    async def test_rename_returns_200(self, client: AsyncClient, flavor_id: str, image_id: str):
        created = await create_test_server(client, flavor_id, image_id, name="original")
        resp = await client.patch(
            f"/api/v1/servers/{created['id']}",
            json={"name": "renamed"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "renamed"

    async def test_update_nonexistent_returns_404(self, client: AsyncClient):
        resp = await client.patch(
            "/api/v1/servers/nonexistent-id",
            json={"name": "new-name"},
        )
        assert resp.status_code == 404

    async def test_update_deleted_returns_409(
        self, client: AsyncClient, flavor_id: str, image_id: str
    ):
        server = await create_test_server(client, flavor_id, image_id)
        server_id = server["id"]
        await client.delete(f"/api/v1/servers/{server_id}")

        resp = await client.patch(
            f"/api/v1/servers/{server_id}",
            json={"name": "new-name"},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "SERVER_DELETED"


class TestDeleteServer:
    async def test_delete_returns_204(self, client: AsyncClient, flavor_id: str, image_id: str):
        created = await create_test_server(client, flavor_id, image_id)
        resp = await client.delete(f"/api/v1/servers/{created['id']}")
        assert resp.status_code == 204

    async def test_delete_nonexistent_returns_404(self, client: AsyncClient):
        resp = await client.delete("/api/v1/servers/nonexistent-id")
        assert resp.status_code == 404

    async def test_delete_already_deleted_returns_404(
        self, client: AsyncClient, flavor_id: str, image_id: str
    ):
        server = await create_test_server(client, flavor_id, image_id)
        server_id = server["id"]
        await client.delete(f"/api/v1/servers/{server_id}")

        resp = await client.delete(f"/api/v1/servers/{server_id}")
        assert resp.status_code == 404
