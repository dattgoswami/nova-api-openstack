from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.pagination import PaginationParams
from app.dependencies import get_flavor_service
from app.infra.openstack.base import FlavorRecord
from app.schemas.common import PaginatedResponse
from app.schemas.flavor import FlavorResponse
from app.services.flavor_service import FlavorService

router = APIRouter(prefix="/flavors", tags=["flavors"])


def _to_response(record: FlavorRecord) -> FlavorResponse:
    return FlavorResponse(
        id=record.id,
        name=record.name,
        vcpus=record.vcpus,
        ram_mb=record.ram_mb,
        disk_gb=record.disk_gb,
    )


@router.get(
    "",
    response_model=PaginatedResponse[FlavorResponse],
    summary="List available flavors (paginated)",
)
async def list_flavors(
    pagination: Annotated[PaginationParams, Depends()],
    service: Annotated[FlavorService, Depends(get_flavor_service)],
) -> PaginatedResponse[FlavorResponse]:
    records, total = await service.list(limit=pagination.limit, offset=pagination.offset)
    items = [_to_response(r) for r in records]
    return PaginatedResponse.build(
        items=items, total=total, limit=pagination.limit, offset=pagination.offset
    )


@router.get(
    "/{flavor_id}",
    response_model=FlavorResponse,
    summary="Get a flavor by ID",
)
async def get_flavor(
    flavor_id: str,
    service: Annotated[FlavorService, Depends(get_flavor_service)],
) -> FlavorResponse:
    record = await service.get(flavor_id)
    return _to_response(record)
