from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.pagination import PaginationParams
from app.dependencies import get_server_service
from app.infra.openstack.base import ServerRecord
from app.schemas.common import PaginatedResponse
from app.schemas.server import ServerAction, ServerCreate, ServerResponse, ServerUpdate
from app.services.server_service import ServerService

router = APIRouter(prefix="/servers", tags=["servers"])


def _to_response(record: ServerRecord) -> ServerResponse:
    return ServerResponse(
        id=record.id,
        name=record.name,
        status=record.status,
        flavor_id=record.flavor_id,
        image_id=record.image_id,
        ip_address=record.ip_address,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.post(
    "",
    response_model=ServerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new server (boot VM)",
)
async def create_server(
    payload: ServerCreate,
    service: Annotated[ServerService, Depends(get_server_service)],
) -> ServerResponse:
    record = await service.create(payload)
    return _to_response(record)


@router.get(
    "",
    response_model=PaginatedResponse[ServerResponse],
    summary="List servers (paginated)",
)
async def list_servers(
    pagination: Annotated[PaginationParams, Depends()],
    service: Annotated[ServerService, Depends(get_server_service)],
) -> PaginatedResponse[ServerResponse]:
    records, total = await service.list(limit=pagination.limit, offset=pagination.offset)
    items = [_to_response(r) for r in records]
    return PaginatedResponse.build(
        items=items, total=total, limit=pagination.limit, offset=pagination.offset
    )


@router.get(
    "/{server_id}",
    response_model=ServerResponse,
    summary="Get a server by ID",
)
async def get_server(
    server_id: str,
    service: Annotated[ServerService, Depends(get_server_service)],
) -> ServerResponse:
    record = await service.get(server_id)
    return _to_response(record)


@router.patch(
    "/{server_id}",
    response_model=ServerResponse,
    summary="Update server metadata (rename)",
)
async def update_server(
    server_id: str,
    payload: ServerUpdate,
    service: Annotated[ServerService, Depends(get_server_service)],
) -> ServerResponse:
    record = await service.update(server_id, payload)
    return _to_response(record)


@router.delete(
    "/{server_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a server",
)
async def delete_server(
    server_id: str,
    service: Annotated[ServerService, Depends(get_server_service)],
) -> None:
    await service.delete(server_id)


@router.post(
    "/{server_id}/action",
    response_model=ServerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Perform a lifecycle action (start/stop/reboot/resize)",
)
async def server_action(
    server_id: str,
    payload: ServerAction,
    service: Annotated[ServerService, Depends(get_server_service)],
) -> ServerResponse:
    record = await service.perform_action(server_id, payload)
    return _to_response(record)
