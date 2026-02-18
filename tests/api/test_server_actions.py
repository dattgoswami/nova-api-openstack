"""
Tests for POST /api/v1/servers/{id}/action — state machine actions.
"""

from httpx import AsyncClient


async def create_server(client: AsyncClient, flavor_id: str, image_id: str) -> dict:
    resp = await client.post(
        "/api/v1/servers",
        json={"name": "action-test", "flavor_id": flavor_id, "image_id": image_id},
    )
    assert resp.status_code == 201
    return resp.json()


async def do_action(client: AsyncClient, server_id: str, action: str, **kwargs) -> dict:
    body = {"action": action, **kwargs}
    resp = await client.post(f"/api/v1/servers/{server_id}/action", json=body)
    return resp


class TestStopAction:
    async def test_stop_active_returns_202_shutoff(
        self, client: AsyncClient, flavor_id: str, image_id: str
    ):
        server = await create_server(client, flavor_id, image_id)
        resp = await do_action(client, server["id"], "stop")
        assert resp.status_code == 202
        assert resp.json()["status"] == "SHUTOFF"

    async def test_stop_shutoff_returns_409(
        self, client: AsyncClient, flavor_id: str, image_id: str
    ):
        server = await create_server(client, flavor_id, image_id)
        await do_action(client, server["id"], "stop")
        resp = await do_action(client, server["id"], "stop")
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


class TestStartAction:
    async def test_start_shutoff_returns_202_active(
        self, client: AsyncClient, flavor_id: str, image_id: str
    ):
        server = await create_server(client, flavor_id, image_id)
        await do_action(client, server["id"], "stop")
        resp = await do_action(client, server["id"], "start")
        assert resp.status_code == 202
        assert resp.json()["status"] == "ACTIVE"

    async def test_start_active_returns_409(
        self, client: AsyncClient, flavor_id: str, image_id: str
    ):
        server = await create_server(client, flavor_id, image_id)
        resp = await do_action(client, server["id"], "start")
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


class TestRebootAction:
    async def test_reboot_active_returns_202_active(
        self, client: AsyncClient, flavor_id: str, image_id: str
    ):
        server = await create_server(client, flavor_id, image_id)
        resp = await do_action(client, server["id"], "reboot")
        assert resp.status_code == 202
        assert resp.json()["status"] == "ACTIVE"

    async def test_reboot_shutoff_returns_409(
        self, client: AsyncClient, flavor_id: str, image_id: str
    ):
        server = await create_server(client, flavor_id, image_id)
        await do_action(client, server["id"], "stop")
        resp = await do_action(client, server["id"], "reboot")
        assert resp.status_code == 409


class TestResizeAction:
    async def test_resize_active_with_new_flavor_returns_202(
        self, client: AsyncClient, flavor_id: str, flavor_id_2: str, image_id: str
    ):
        server = await create_server(client, flavor_id, image_id)
        resp = await do_action(client, server["id"], "resize", flavor_id=flavor_id_2)
        assert resp.status_code == 202
        assert resp.json()["flavor_id"] == flavor_id_2

    async def test_resize_without_flavor_id_returns_422(
        self, client: AsyncClient, flavor_id: str, image_id: str
    ):
        server = await create_server(client, flavor_id, image_id)
        resp = await client.post(
            f"/api/v1/servers/{server['id']}/action", json={"action": "resize"}
        )
        assert resp.status_code == 422

    async def test_resize_with_nonexistent_flavor_returns_404(
        self, client: AsyncClient, flavor_id: str, image_id: str
    ):
        server = await create_server(client, flavor_id, image_id)
        resp = await do_action(client, server["id"], "resize", flavor_id="nonexistent-id")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "FLAVOR_NOT_FOUND"

    async def test_resize_shutoff_returns_409(
        self, client: AsyncClient, flavor_id: str, flavor_id_2: str, image_id: str
    ):
        server = await create_server(client, flavor_id, image_id)
        await do_action(client, server["id"], "stop")
        resp = await do_action(client, server["id"], "resize", flavor_id=flavor_id_2)
        assert resp.status_code == 409


class TestActionErrors:
    async def test_action_on_nonexistent_server_returns_404(self, client: AsyncClient):
        resp = await client.post("/api/v1/servers/nonexistent-id/action", json={"action": "stop"})
        assert resp.status_code == 404

    async def test_action_on_deleted_server_returns_404(
        self, client: AsyncClient, flavor_id: str, image_id: str
    ):
        server = await create_server(client, flavor_id, image_id)
        server_id = server["id"]
        await client.delete(f"/api/v1/servers/{server_id}")
        resp = await client.post(f"/api/v1/servers/{server_id}/action", json={"action": "stop"})
        assert resp.status_code == 404

    async def test_invalid_action_name_returns_422(
        self, client: AsyncClient, flavor_id: str, image_id: str
    ):
        server = await create_server(client, flavor_id, image_id)
        resp = await client.post(
            f"/api/v1/servers/{server['id']}/action",
            json={"action": "explode"},
        )
        assert resp.status_code == 422

    async def test_start_with_flavor_id_returns_422(
        self, client: AsyncClient, flavor_id: str, flavor_id_2: str, image_id: str
    ):
        server = await create_server(client, flavor_id, image_id)
        await do_action(client, server["id"], "stop")
        resp = await client.post(
            f"/api/v1/servers/{server['id']}/action",
            json={"action": "start", "flavor_id": flavor_id_2},
        )
        assert resp.status_code == 422
