"""FastAPI exception handlers for HTTP, validation, and unexpected errors."""
import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core.exceptions import DuplicateResourceError, ResourceNotFoundError

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Return a JSON error body with the original HTTP status code."""
    logger.warning("HTTP %s on %s: %s", exc.status_code, request.url.path, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


async def conflict_exception_handler(request: Request, exc: DuplicateResourceError) -> JSONResponse:
    """Return HTTP 409 Conflict for duplicate-resource errors."""
    logger.warning("Conflict on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"error": str(exc)},
    )


async def not_found_exception_handler(request: Request, exc: ResourceNotFoundError) -> JSONResponse:
    """Return HTTP 404 Not Found for missing-resource errors."""
    logger.warning("Not found on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"error": str(exc)},
    )


async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Return HTTP 422 with field-level validation error details."""
    logger.warning("Validation error on %s: %s", request.url.path, exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"error": "Validation error", "details": exc.errors()},
    )


async def unhandled_exception_handler(request: Request, _exc: Exception) -> JSONResponse:
    """Catch-all handler that logs the traceback and returns HTTP 500."""
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all exception handlers to the FastAPI application."""
    app.add_exception_handler(
        HTTPException, http_exception_handler  # type: ignore[arg-type]
    )
    app.add_exception_handler(
        DuplicateResourceError, conflict_exception_handler,  # type: ignore[arg-type]
    )
    app.add_exception_handler(
        ResourceNotFoundError, not_found_exception_handler,  # type: ignore[arg-type]
    )
    app.add_exception_handler(
        ValidationError, validation_exception_handler,  # type: ignore[arg-type]
    )
    app.add_exception_handler(
        Exception, unhandled_exception_handler
    )
