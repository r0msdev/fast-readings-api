"""RabbitMQ messaging backend using the pika library."""
import logging
from typing import Any

import pika

from app.config import settings

logger = logging.getLogger('weather')


class _State:  # pylint: disable=too-few-public-methods
    channel: Any = None


_state = _State()


def get_channel() -> Any:
    """Open a new connection and return a fresh channel."""
    params = pika.URLParameters(settings.rabbitmq_url)
    connection = pika.BlockingConnection(params)
    return connection.channel()


def ping() -> None:
    """Open and immediately close a connection to verify broker reachability."""
    conn = pika.BlockingConnection(pika.URLParameters(settings.rabbitmq_url))
    conn.close()


def publish(queue_name: str, body: str, message_id: str | None = None) -> None:
    """Publish a persistent message to the named queue."""
    if _state.channel is None or not _state.channel.connection.is_open:
        _state.channel = get_channel()
        _state.channel.queue_declare(queue=queue_name, durable=True)
    _state.channel.basic_publish(
        exchange='',
        routing_key=queue_name,
        body=body,
        properties=pika.BasicProperties(
            delivery_mode=pika.DeliveryMode.Persistent,
            message_id=message_id,
        ),
    )
