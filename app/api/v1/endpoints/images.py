from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.pagination import PaginationParams
from app.dependencies import get_image_service
from app.infra.openstack.base import ImageRecord
from app.schemas.common import PaginatedResponse
from app.schemas.image import ImageResponse
from app.services.image_service import ImageService

router = APIRouter(prefix="/images", tags=["images"])


def _to_response(record: ImageRecord) -> ImageResponse:
    return ImageResponse(
        id=record.id,
        name=record.name,
        os_distro=record.os_distro,
        min_disk_gb=record.min_disk_gb,
        size_bytes=record.size_bytes,
        status=record.status,
    )


@router.get(
    "",
    response_model=PaginatedResponse[ImageResponse],
    summary="List available images (paginated)",
)
async def list_images(
    pagination: Annotated[PaginationParams, Depends()],
    service: Annotated[ImageService, Depends(get_image_service)],
) -> PaginatedResponse[ImageResponse]:
    records, total = await service.list(limit=pagination.limit, offset=pagination.offset)
    items = [_to_response(r) for r in records]
    return PaginatedResponse.build(
        items=items, total=total, limit=pagination.limit, offset=pagination.offset
    )


@router.get(
    "/{image_id}",
    response_model=ImageResponse,
    summary="Get an image by ID",
)
async def get_image(
    image_id: str,
    service: Annotated[ImageService, Depends(get_image_service)],
) -> ImageResponse:
    record = await service.get(image_id)
    return _to_response(record)
