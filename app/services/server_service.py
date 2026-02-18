"""
Server service — business logic layer for VM lifecycle management.

Enforces the state machine on top of the OpenStack infra layer.
All state transition validation happens here before any infra call.
"""

import logging

from app.core.exceptions import (
    FlavorNotFoundError,
    ImageNotFoundError,
    InvalidStateTransitionError,
    ServerDeletedError,
    ServerNotFoundError,
)
from app.infra.openstack.base import OpenStackClientBase, ServerRecord
from app.models.server import ServerStatus
from app.schemas.server import ServerAction, ServerCreate, ServerUpdate

logger = logging.getLogger(__name__)

# State machine: maps current status → allowed actions → next status
VALID_TRANSITIONS: dict[ServerStatus, dict[str, ServerStatus]] = {
    ServerStatus.ACTIVE: {
        "stop": ServerStatus.SHUTOFF,
        "reboot": ServerStatus.ACTIVE,
        "resize": ServerStatus.ACTIVE,
    },
    ServerStatus.SHUTOFF: {
        "start": ServerStatus.ACTIVE,
    },
    ServerStatus.BUILD: {},  # system-managed, no user actions allowed
    ServerStatus.REBOOT: {},  # system-managed
    ServerStatus.RESIZE: {},  # system-managed
    ServerStatus.VERIFY_RESIZE: {
        "confirm_resize": ServerStatus.ACTIVE,
    },
}


class ServerService:
    def __init__(self, client: OpenStackClientBase) -> None:
        self._client = client

    async def create(self, payload: ServerCreate) -> ServerRecord:
        # Validate flavor and image exist before creating
        flavor = await self._client.get_flavor(payload.flavor_id)
        if flavor is None:
            raise FlavorNotFoundError(payload.flavor_id)

        image = await self._client.get_image(payload.image_id)
        if image is None:
            raise ImageNotFoundError(payload.image_id)

        server = await self._client.create_server(
            name=payload.name,
            flavor_id=payload.flavor_id,
            image_id=payload.image_id,
        )
        logger.info(
            "Server created",
            extra={
                "server_id": server.id,
                "server_name": server.name,
                "flavor_id": server.flavor_id,
                "image_id": server.image_id,
                "status": server.status.value,
            },
        )
        return server

    async def get(self, server_id: str) -> ServerRecord:
        server = await self._client.get_server(server_id)
        if server is None:
            raise ServerNotFoundError(server_id)
        if server.status == ServerStatus.DELETED:
            raise ServerNotFoundError(server_id)
        return server

    async def list(self, limit: int, offset: int) -> tuple[list[ServerRecord], int]:
        return await self._client.list_servers(limit=limit, offset=offset)

    async def update(self, server_id: str, payload: ServerUpdate) -> ServerRecord:
        server = await self._client.get_server(server_id)
        if server is None:
            raise ServerNotFoundError(server_id)
        if server.status == ServerStatus.DELETED:
            raise ServerDeletedError(server_id)

        name = payload.name if payload.name is not None else server.name
        updated = await self._client.update_server(server_id=server_id, name=name)
        logger.info("Server updated", extra={"server_id": server_id, "server_name": updated.name})
        return updated

    async def delete(self, server_id: str) -> None:
        server = await self._client.get_server(server_id)
        if server is None:
            raise ServerNotFoundError(server_id)
        if server.status == ServerStatus.DELETED:
            raise ServerNotFoundError(server_id)
        await self._client.delete_server(server_id)
        logger.info("Server deleted", extra={"server_id": server_id})

    async def perform_action(self, server_id: str, payload: ServerAction) -> ServerRecord:
        server = await self._client.get_server(server_id)
        if server is None:
            raise ServerNotFoundError(server_id)
        if server.status == ServerStatus.DELETED:
            raise ServerNotFoundError(server_id)

        # Validate state transition
        allowed = VALID_TRANSITIONS.get(server.status, {})
        if payload.action not in allowed:
            logger.warning(
                "Invalid state transition attempt",
                extra={
                    "server_id": server_id,
                    "current_status": server.status.value,
                    "action": payload.action,
                },
            )
            raise InvalidStateTransitionError(
                current_status=server.status.value,
                action=payload.action,
            )

        kwargs: dict[str, object] = {}
        if payload.action == "resize" and payload.flavor_id:
            # Validate target flavor exists
            flavor = await self._client.get_flavor(payload.flavor_id)
            if flavor is None:
                raise FlavorNotFoundError(payload.flavor_id)
            kwargs["flavor_id"] = payload.flavor_id

        logger.info(
            "State transition",
            extra={
                "server_id": server_id,
                "from_status": server.status.value,
                "action": payload.action,
            },
        )
        result = await self._client.perform_action(
            server_id=server_id,
            action=payload.action,
            **kwargs,
        )
        logger.info(
            "State transition complete",
            extra={"server_id": server_id, "new_status": result.status.value},
        )
        return result
