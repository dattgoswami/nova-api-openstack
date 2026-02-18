import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base application exception."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, details: object = None) -> None:
        self.message = message
        self.details = details
        super().__init__(message)


class ServerNotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "SERVER_NOT_FOUND"

    def __init__(self, server_id: str) -> None:
        super().__init__(f"Server {server_id} not found")


class FlavorNotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "FLAVOR_NOT_FOUND"

    def __init__(self, flavor_id: str) -> None:
        super().__init__(f"Flavor {flavor_id} not found")


class ImageNotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "IMAGE_NOT_FOUND"

    def __init__(self, image_id: str) -> None:
        super().__init__(f"Image {image_id} not found")


class InvalidStateTransitionError(AppException):
    status_code = status.HTTP_409_CONFLICT
    error_code = "INVALID_STATE_TRANSITION"

    def __init__(self, current_status: str, action: str) -> None:
        super().__init__(
            f"Cannot perform action '{action}' on server in status '{current_status}'",
            details={"current_status": current_status, "action": action},
        )


class ServerDeletedError(AppException):
    status_code = status.HTTP_409_CONFLICT
    error_code = "SERVER_DELETED"

    def __init__(self, server_id: str) -> None:
        super().__init__(f"Server {server_id} has been deleted and cannot be modified")


def _error_response(code: str, message: str, details: object = None) -> JSONResponse:
    return JSONResponse(
        content={"error": {"code": code, "message": message, "details": details}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        log_fn = logger.error if exc.status_code >= 500 else logger.warning
        log_fn(
            exc.error_code,
            extra={
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "path": request.url.path,
                "detail": exc.message,
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {"code": exc.error_code, "message": exc.message, "details": exc.details}
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Convert errors to plain dicts to ensure JSON serializability
        errors = [
            {
                "loc": list(e.get("loc", [])),
                "msg": e.get("msg", ""),
                "type": e.get("type", ""),
            }
            for e in exc.errors()
        ]
        logger.info(
            "Request validation failed",
            extra={"path": request.url.path, "error_count": len(errors)},
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": errors,
                }
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled exception",
            exc_info=True,
            extra={"path": request.url.path, "exc_type": type(exc).__name__},
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": None,
                }
            },
        )
