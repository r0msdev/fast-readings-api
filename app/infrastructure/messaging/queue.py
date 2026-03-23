"""Messaging facade — routes publish() and ping() to the configured backend.
Backend-specific logic lives in rabbitmq.py and servicebus.py.
"""
from collections.abc import Callable
from typing import Any

from app.config import settings


class _State:  # pylint: disable=too-few-public-methods
    backend: Any = None


_state = _State()


def _get_backend():
    if _state.backend is None:
        if settings.messaging_backend == 'servicebus':
            from app.infrastructure.messaging import servicebus  # pylint: disable=import-outside-toplevel
            _state.backend = servicebus
        else:
            from app.infrastructure.messaging import rabbitmq  # pylint: disable=import-outside-toplevel
            _state.backend = rabbitmq
    return _state.backend


def ping() -> None:
    """Verify broker reachability using the configured backend."""
    _get_backend().ping()


def publish(queue_name: str, body: str, message_id: str | None = None) -> None:
    """Publish a message to the named queue using the configured backend."""
    _get_backend().publish(queue_name, body, message_id)


def consume(
    queue_name: str,
    callback: Callable[[str], None],
    heartbeat_fn: Callable[[], None] | None = None,
) -> None:
    """Block forever, calling callback(body_str) for each message received."""
    _get_backend().consume(queue_name, callback, heartbeat_fn)


def close() -> None:
    """Release any persistent connections held by the configured backend."""
    if _state.backend is not None:
        _state.backend.close()
