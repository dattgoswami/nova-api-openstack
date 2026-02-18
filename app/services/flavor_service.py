import logging

from app.core.exceptions import FlavorNotFoundError
from app.infra.openstack.base import FlavorRecord, OpenStackClientBase

logger = logging.getLogger(__name__)


class FlavorService:
    def __init__(self, client: OpenStackClientBase) -> None:
        self._client = client

    async def get(self, flavor_id: str) -> FlavorRecord:
        flavor = await self._client.get_flavor(flavor_id)
        if flavor is None:
            raise FlavorNotFoundError(flavor_id)
        logger.debug("Flavor fetched", extra={"flavor_id": flavor_id})
        return flavor

    async def list(self, limit: int, offset: int) -> tuple[list[FlavorRecord], int]:
        records, total = await self._client.list_flavors(limit=limit, offset=offset)
        logger.debug("Flavors listed", extra={"limit": limit, "offset": offset, "total": total})
        return records, total
