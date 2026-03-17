"""ASGI middleware for correlation-ID propagation and structured logging."""
import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.correlation import CORRELATION_ID_HEADER, get_correlation_id, set_correlation_id


class CorrelationIdFilter(logging.Filter):  # pylint: disable=too-few-public-methods
    """Injects the current correlation ID into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()  # type: ignore[attr-defined]
        return True


class CorrelationIdMiddleware(BaseHTTPMiddleware):  # pylint: disable=too-few-public-methods
    """Reads X-Correlation-ID from the request (or generates one) and echoes
    it back in the response header. Stores it in a ContextVar so it can be
    included in log records via CorrelationIdFilter."""

    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or str(uuid.uuid4())
        set_correlation_id(correlation_id)
        response = await call_next(request)
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response
