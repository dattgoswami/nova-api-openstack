from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
    next_offset: int | None

    @classmethod
    def build(cls, items: list[T], total: int, limit: int, offset: int) -> "PaginatedResponse[T]":
        next_offset = offset + limit if offset + limit < total else None
        return cls(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            next_offset=next_offset,
        )
