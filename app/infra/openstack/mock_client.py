"""
MockOpenStackClient — implements OpenStackClientBase against the SQLAlchemy async DB.

This allows full end-to-end testing without a real OpenStack cluster. The state
machine transitions are applied here as the 'compute backend' would do them.
"""

import ipaddress
import random
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.openstack.base import (
    FlavorRecord,
    ImageRecord,
    OpenStackClientBase,
    ServerRecord,
)
from app.models.flavor import Flavor
from app.models.image import Image
from app.models.server import Server, ServerStatus


def _server_to_record(server: Server) -> ServerRecord:
    now = datetime.now(UTC)
    return ServerRecord(
        id=server.id,
        name=server.name,
        status=server.status,
        flavor_id=server.flavor_id,
        image_id=server.image_id,
        ip_address=server.ip_address,
        created_at=server.created_at if server.created_at else now,
        updated_at=server.updated_at if server.updated_at else now,
    )


def _flavor_to_record(flavor: Flavor) -> FlavorRecord:
    return FlavorRecord(
        id=flavor.id,
        name=flavor.name,
        vcpus=flavor.vcpus,
        ram_mb=flavor.ram_mb,
        disk_gb=flavor.disk_gb,
    )


def _image_to_record(image: Image) -> ImageRecord:
    return ImageRecord(
        id=image.id,
        name=image.name,
        os_distro=image.os_distro,
        min_disk_gb=image.min_disk_gb,
        size_bytes=image.size_bytes,
        status=image.status,
    )


def _random_ip() -> str:
    return str(ipaddress.IPv4Address(random.randint(0x0A000001, 0x0AFFFFFF)))


# Valid transitions mirror the state machine definition
_ACTION_TRANSITIONS: dict[ServerStatus, dict[str, ServerStatus]] = {
    ServerStatus.ACTIVE: {
        "stop": ServerStatus.SHUTOFF,
        "reboot": ServerStatus.ACTIVE,  # mock: instant reboot
        "resize": ServerStatus.ACTIVE,  # mock: instant resize (skip VERIFY_RESIZE)
    },
    ServerStatus.SHUTOFF: {
        "start": ServerStatus.ACTIVE,
    },
}


class MockOpenStackClient(OpenStackClientBase):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_server(self, name: str, flavor_id: str, image_id: str) -> ServerRecord:
        server = Server(
            id=str(uuid.uuid4()),
            name=name,
            status=ServerStatus.ACTIVE,  # mock: skip BUILD phase, go straight to ACTIVE
            flavor_id=flavor_id,
            image_id=image_id,
            ip_address=_random_ip(),
        )
        self._session.add(server)
        await self._session.flush()
        await self._session.refresh(server)
        return _server_to_record(server)

    async def get_server(self, server_id: str) -> ServerRecord | None:
        result = await self._session.execute(select(Server).where(Server.id == server_id))
        server = result.scalar_one_or_none()
        return _server_to_record(server) if server else None

    async def list_servers(self, limit: int, offset: int) -> tuple[list[ServerRecord], int]:
        count_result = await self._session.execute(
            select(func.count()).select_from(Server).where(Server.status != ServerStatus.DELETED)
        )
        total = count_result.scalar_one()

        result = await self._session.execute(
            select(Server)
            .where(Server.status != ServerStatus.DELETED)
            .order_by(Server.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        servers = list(result.scalars().all())
        return [_server_to_record(s) for s in servers], total

    async def update_server(self, server_id: str, name: str) -> ServerRecord:
        result = await self._session.execute(select(Server).where(Server.id == server_id))
        server = result.scalar_one_or_none()
        if server is None:
            raise ValueError(f"Server {server_id} not found")
        server.name = name
        server.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(server)
        return _server_to_record(server)

    async def delete_server(self, server_id: str) -> None:
        result = await self._session.execute(select(Server).where(Server.id == server_id))
        server = result.scalar_one_or_none()
        if server is None:
            raise ValueError(f"Server {server_id} not found")
        server.status = ServerStatus.DELETED
        server.updated_at = datetime.now(UTC)
        await self._session.flush()

    async def perform_action(self, server_id: str, action: str, **kwargs: object) -> ServerRecord:
        result = await self._session.execute(select(Server).where(Server.id == server_id))
        server = result.scalar_one_or_none()
        if server is None:
            raise ValueError(f"Server {server_id} not found")

        transitions = _ACTION_TRANSITIONS.get(server.status, {})
        new_status = transitions.get(action)
        if new_status is None:
            raise ValueError(
                f"Cannot perform action '{action}' on server in status '{server.status}'"
            )

        server.status = new_status

        # For resize, update the flavor_id
        if action == "resize" and "flavor_id" in kwargs:
            server.flavor_id = str(kwargs["flavor_id"])

        server.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(server)
        return _server_to_record(server)

    # --- Flavor ---

    async def get_flavor(self, flavor_id: str) -> FlavorRecord | None:
        result = await self._session.execute(select(Flavor).where(Flavor.id == flavor_id))
        flavor = result.scalar_one_or_none()
        return _flavor_to_record(flavor) if flavor else None

    async def list_flavors(self, limit: int, offset: int) -> tuple[list[FlavorRecord], int]:
        count_result = await self._session.execute(select(func.count()).select_from(Flavor))
        total = count_result.scalar_one()

        result = await self._session.execute(
            select(Flavor).order_by(Flavor.name).limit(limit).offset(offset)
        )
        flavors = list(result.scalars().all())
        return [_flavor_to_record(f) for f in flavors], total

    # --- Image ---

    async def get_image(self, image_id: str) -> ImageRecord | None:
        result = await self._session.execute(select(Image).where(Image.id == image_id))
        image = result.scalar_one_or_none()
        return _image_to_record(image) if image else None

    async def list_images(self, limit: int, offset: int) -> tuple[list[ImageRecord], int]:
        count_result = await self._session.execute(select(func.count()).select_from(Image))
        total = count_result.scalar_one()

        result = await self._session.execute(
            select(Image).order_by(Image.name).limit(limit).offset(offset)
        )
        images = list(result.scalars().all())
        return [_image_to_record(i) for i in images], total
