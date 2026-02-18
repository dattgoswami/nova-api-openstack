"""Application middleware."""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import request_id_var


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Extracts or generates a request correlation ID for every request.

    Behaviour:
    - If the client sends an ``X-Request-ID`` header, that value is reused.
    - Otherwise a fresh UUID4 hex string is generated.
    - The ID is stored in ``request.state.request_id``, injected into the
      ``request_id_var`` ContextVar (so all loggers pick it up automatically),
      and echoed back in the ``X-Request-ID`` response header.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = request_id
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_var.reset(token)
