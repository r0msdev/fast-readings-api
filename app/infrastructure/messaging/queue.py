"""Messaging facade — routes publish() and ping() to the configured backend.
Backend-specific logic lives in rabbitmq.py and servicebus.py.
"""
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
