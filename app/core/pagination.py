from fastapi import Query


class PaginationParams:
    def __init__(
        self,
        limit: int = Query(default=20, ge=1, le=100, description="Number of items to return"),
        offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    ) -> None:
        self.limit = limit
        self.offset = offset
