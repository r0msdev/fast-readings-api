"""Context-variable helpers for propagating correlation IDs across async tasks."""
from contextvars import ContextVar

CORRELATION_ID_HEADER = 'X-Correlation-ID'

_correlation_id: ContextVar[str] = ContextVar('correlation_id', default='')


def get_correlation_id() -> str:
    """Return the correlation ID for the current request context."""
    return _correlation_id.get()


def set_correlation_id(value: str) -> None:
    """Set the correlation ID for the current request context."""
    _correlation_id.set(value)
