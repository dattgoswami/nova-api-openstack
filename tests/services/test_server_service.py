"""
Unit tests for the server service state machine.
Tests service layer directly against the mock client backed by an in-memory DB.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    FlavorNotFoundError,
    ImageNotFoundError,
    InvalidStateTransitionError,
    ServerDeletedError,
    ServerNotFoundError,
)
from app.infra.openstack.mock_client import MockOpenStackClient
from app.schemas.server import ServerAction, ServerCreate, ServerUpdate
from app.services.server_service import ServerService


async def make_service(session: AsyncSession) -> ServerService:
    client = MockOpenStackClient(session)
    return ServerService(client)


class TestServerServiceCreate:
    async def test_create_valid(self, test_session: AsyncSession, seed_flavors, seed_images):
        service = await make_service(test_session)
        flavor_id = seed_flavors[0].id
        image_id = seed_images[0].id

        record = await service.create(
            ServerCreate(name="test", flavor_id=flavor_id, image_id=image_id)
        )
        assert record.name == "test"
        assert record.flavor_id == flavor_id

    async def test_create_invalid_flavor_raises(self, test_session: AsyncSession, seed_images):
        service = await make_service(test_session)
        with pytest.raises(FlavorNotFoundError):
            await service.create(
                ServerCreate(name="test", flavor_id="bad", image_id=seed_images[0].id)
            )

    async def test_create_invalid_image_raises(self, test_session: AsyncSession, seed_flavors):
        service = await make_service(test_session)
        with pytest.raises(ImageNotFoundError):
            await service.create(
                ServerCreate(name="test", flavor_id=seed_flavors[0].id, image_id="bad")
            )


class TestServerServiceGet:
    async def test_get_existing(self, test_session: AsyncSession, seed_flavors, seed_images):
        service = await make_service(test_session)
        created = await service.create(
            ServerCreate(
                name="server",
                flavor_id=seed_flavors[0].id,
                image_id=seed_images[0].id,
            )
        )
        retrieved = await service.get(created.id)
        assert retrieved.id == created.id

    async def test_get_nonexistent_raises(
        self, test_session: AsyncSession, seed_flavors, seed_images
    ):
        service = await make_service(test_session)
        with pytest.raises(ServerNotFoundError):
            await service.get("nonexistent")

    async def test_get_deleted_raises(self, test_session: AsyncSession, seed_flavors, seed_images):
        service = await make_service(test_session)
        created = await service.create(
            ServerCreate(
                name="server",
                flavor_id=seed_flavors[0].id,
                image_id=seed_images[0].id,
            )
        )
        await service.delete(created.id)
        with pytest.raises(ServerNotFoundError):
            await service.get(created.id)


class TestServerServiceStateMachine:
    async def _create(self, service: ServerService, seed_flavors, seed_images):
        return await service.create(
            ServerCreate(
                name="vm",
                flavor_id=seed_flavors[0].id,
                image_id=seed_images[0].id,
            )
        )

    async def test_stop_active_succeeds(
        self, test_session: AsyncSession, seed_flavors, seed_images
    ):
        service = await make_service(test_session)
        server = await self._create(service, seed_flavors, seed_images)
        updated = await service.perform_action(server.id, ServerAction(action="stop"))
        assert updated.status.value == "SHUTOFF"

    async def test_start_shutoff_succeeds(
        self, test_session: AsyncSession, seed_flavors, seed_images
    ):
        service = await make_service(test_session)
        server = await self._create(service, seed_flavors, seed_images)
        await service.perform_action(server.id, ServerAction(action="stop"))
        updated = await service.perform_action(server.id, ServerAction(action="start"))
        assert updated.status.value == "ACTIVE"

    async def test_stop_shutoff_raises_invalid_transition(
        self, test_session: AsyncSession, seed_flavors, seed_images
    ):
        service = await make_service(test_session)
        server = await self._create(service, seed_flavors, seed_images)
        await service.perform_action(server.id, ServerAction(action="stop"))
        with pytest.raises(InvalidStateTransitionError):
            await service.perform_action(server.id, ServerAction(action="stop"))

    async def test_start_active_raises_invalid_transition(
        self, test_session: AsyncSession, seed_flavors, seed_images
    ):
        service = await make_service(test_session)
        server = await self._create(service, seed_flavors, seed_images)
        with pytest.raises(InvalidStateTransitionError):
            await service.perform_action(server.id, ServerAction(action="start"))

    async def test_reboot_active_succeeds(
        self, test_session: AsyncSession, seed_flavors, seed_images
    ):
        service = await make_service(test_session)
        server = await self._create(service, seed_flavors, seed_images)
        updated = await service.perform_action(server.id, ServerAction(action="reboot"))
        assert updated.status.value == "ACTIVE"

    async def test_resize_active_changes_flavor(
        self, test_session: AsyncSession, seed_flavors, seed_images
    ):
        service = await make_service(test_session)
        server = await self._create(service, seed_flavors, seed_images)
        new_flavor_id = seed_flavors[1].id
        updated = await service.perform_action(
            server.id,
            ServerAction(action="resize", flavor_id=new_flavor_id),
        )
        assert updated.flavor_id == new_flavor_id

    async def test_resize_invalid_flavor_raises(
        self, test_session: AsyncSession, seed_flavors, seed_images
    ):
        service = await make_service(test_session)
        server = await self._create(service, seed_flavors, seed_images)
        with pytest.raises(FlavorNotFoundError):
            await service.perform_action(
                server.id,
                ServerAction(action="resize", flavor_id="bad-flavor"),
            )

    async def test_action_on_deleted_server_raises(
        self, test_session: AsyncSession, seed_flavors, seed_images
    ):
        service = await make_service(test_session)
        server = await self._create(service, seed_flavors, seed_images)
        await service.delete(server.id)
        with pytest.raises(ServerNotFoundError):
            await service.perform_action(server.id, ServerAction(action="stop"))


class TestServerServiceUpdate:
    async def test_update_name(self, test_session: AsyncSession, seed_flavors, seed_images):
        service = await make_service(test_session)
        server = await service.create(
            ServerCreate(
                name="old-name",
                flavor_id=seed_flavors[0].id,
                image_id=seed_images[0].id,
            )
        )
        updated = await service.update(server.id, ServerUpdate(name="new-name"))
        assert updated.name == "new-name"

    async def test_update_deleted_raises(
        self, test_session: AsyncSession, seed_flavors, seed_images
    ):
        service = await make_service(test_session)
        server = await service.create(
            ServerCreate(
                name="server",
                flavor_id=seed_flavors[0].id,
                image_id=seed_images[0].id,
            )
        )
        await service.delete(server.id)
        with pytest.raises(ServerDeletedError):
            await service.update(server.id, ServerUpdate(name="new-name"))
