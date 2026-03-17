"""RabbitMQ messaging backend using the pika library."""
import logging
from collections.abc import Callable

import pika

from app.config import settings

logger = logging.getLogger('weather')


def ping() -> None:
    """Open and immediately close a connection to verify broker reachability."""
    conn = pika.BlockingConnection(pika.URLParameters(settings.rabbitmq_url))
    conn.close()


def publish(queue_name: str, body: str, message_id: str | None = None) -> None:
    """Publish a persistent message to the named queue.

    Opens a fresh connection per call — safe across threads and reconnects.
    """
    params = pika.URLParameters(settings.rabbitmq_url)
    connection = pika.BlockingConnection(params)
    try:
        channel = connection.channel()
        channel.queue_declare(queue=queue_name, durable=True)
        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=body,
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent,
                message_id=message_id,
            ),
        )
    finally:
        connection.close()


def consume(
    queue_name: str,
    callback: Callable[[str], None],
    heartbeat_fn: Callable[[], None] | None = None,
) -> None:
    """Block forever, calling callback(body_str) for each message received.

    Acks on success, nacks-without-requeue on unhandled exception.
    An optional heartbeat_fn() is called every 30 s to keep the connection alive.
    """
    heartbeat_interval = 30
    params = pika.URLParameters(settings.rabbitmq_url)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_qos(prefetch_count=1)

    def _heartbeat() -> None:
        if heartbeat_fn:
            heartbeat_fn()
        channel.connection.call_later(heartbeat_interval, _heartbeat)

    def _on_message(ch, method, _properties, raw_body: bytes) -> None:
        try:
            callback(raw_body.decode())
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception:  # pylint: disable=broad-except
            logger.exception('RabbitMQ message processing failed — nacking: %s', raw_body)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    channel.basic_consume(queue=queue_name, on_message_callback=_on_message)
    channel.connection.call_later(heartbeat_interval, _heartbeat)
    logger.info('RabbitMQ consumer started on queue=%s', queue_name)
    try:
        channel.start_consuming()
    finally:
        if connection.is_open:
            connection.close()
