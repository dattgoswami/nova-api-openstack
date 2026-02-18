from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db
from app.infra.openstack.base import OpenStackClientBase
from app.infra.openstack.mock_client import MockOpenStackClient
from app.services.flavor_service import FlavorService
from app.services.image_service import ImageService
from app.services.server_service import ServerService


async def get_openstack_client(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OpenStackClientBase:
    """Dependency that returns the configured OpenStack client."""
    if settings.use_mock_openstack:
        return MockOpenStackClient(session)
    # In production, return RealOpenStackClient() here
    # from app.infra.openstack.real_client import RealOpenStackClient
    # return RealOpenStackClient()
    return MockOpenStackClient(session)


async def get_server_service(
    client: Annotated[OpenStackClientBase, Depends(get_openstack_client)],
) -> ServerService:
    return ServerService(client)


async def get_flavor_service(
    client: Annotated[OpenStackClientBase, Depends(get_openstack_client)],
) -> FlavorService:
    return FlavorService(client)


async def get_image_service(
    client: Annotated[OpenStackClientBase, Depends(get_openstack_client)],
) -> ImageService:
    return ImageService(client)
