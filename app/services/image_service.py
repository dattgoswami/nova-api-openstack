import logging

from app.core.exceptions import ImageNotFoundError
from app.infra.openstack.base import ImageRecord, OpenStackClientBase

logger = logging.getLogger(__name__)


class ImageService:
    def __init__(self, client: OpenStackClientBase) -> None:
        self._client = client

    async def get(self, image_id: str) -> ImageRecord:
        image = await self._client.get_image(image_id)
        if image is None:
            raise ImageNotFoundError(image_id)
        logger.debug("Image fetched", extra={"image_id": image_id})
        return image

    async def list(self, limit: int, offset: int) -> tuple[list[ImageRecord], int]:
        records, total = await self._client.list_images(limit=limit, offset=offset)
        logger.debug("Images listed", extra={"limit": limit, "offset": offset, "total": total})
        return records, total
