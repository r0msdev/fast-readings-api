"""Azure Service Bus messaging backend."""
# pylint: disable=import-error
import logging
from collections.abc import Callable

from azure.servicebus import (  # type: ignore[import-untyped]
    ServiceBusClient,
    ServiceBusSender,
    ServiceBusMessage,
    ServiceBusError,
)

from app.config import settings

logger = logging.getLogger('weather')

_client: ServiceBusClient | None = None  # pylint: disable=invalid-name
_senders: dict[str, ServiceBusSender] = {}


def _get_client() -> ServiceBusClient:
    """Build and return a ServiceBusClient using namespace credential or connection string."""
    if settings.azure_servicebus_namespace:
        from azure.identity import DefaultAzureCredential  # type: ignore[import-untyped]  # pylint: disable=import-outside-toplevel
        return ServiceBusClient(
            fully_qualified_namespace=settings.azure_servicebus_namespace,
            credential=DefaultAzureCredential(),  # type: ignore[arg-type]
        )
    return ServiceBusClient.from_connection_string(settings.azure_servicebus_connection_string)


def _ensure_sender(queue_name: str) -> ServiceBusSender:
    """Return a cached sender, lazily creating the shared client on first use."""
    global _client  # pylint: disable=global-statement
    if _client is None:
        _client = _get_client()
    if queue_name not in _senders:
        _senders[queue_name] = _client.get_queue_sender(queue_name)  # type: ignore[union-attr]
    return _senders[queue_name]


def ping() -> None:
    """Verify Service Bus reachability by opening and closing a connection."""
    with _get_client() as client:
        client.get_queue_sender(settings.messaging_queue_name)


def publish(queue_name: str, body: str, message_id: str | None = None) -> None:
    """Publish a message, reusing a cached sender. Retries once on a stale connection."""
    for attempt in range(2):
        try:
            sender = _ensure_sender(queue_name)
            sender.send_messages(ServiceBusMessage(body, message_id=message_id))
            return
        except ServiceBusError:
            if attempt == 0:
                _senders.pop(queue_name, None)  # evict stale sender and retry
            else:
                raise


def consume(
    queue_name: str,
    callback: Callable[[str], None],
    heartbeat_fn: Callable[[], None] | None = None,  # pylint: disable=unused-argument
) -> None:
    """Block forever, calling callback(body_str) for each message received.

    heartbeat_fn is accepted for interface compatibility but is not used —
    the Service Bus SDK handles keep-alive internally.
    """
    logger.info('Service Bus consumer started on queue=%s', queue_name)
    with _get_client() as client:
        with client.get_queue_receiver(queue_name) as receiver:
            for msg in receiver:
                body = b"".join(msg.body).decode()  # type: ignore[arg-type]
                try:
                    callback(body)
                    receiver.complete_message(msg)  # type: ignore[arg-type]
                except Exception:  # pylint: disable=broad-except
                    logger.exception(
                        'Service Bus message processing failed — dead-lettering: %s', body
                    )
                    receiver.dead_letter_message(msg)  # type: ignore[arg-type]
