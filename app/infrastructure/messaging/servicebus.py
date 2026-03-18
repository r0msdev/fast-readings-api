"""Azure Service Bus messaging backend."""
# pylint: disable=import-error
import logging
from collections.abc import Callable

from azure.servicebus import (  # type: ignore[import-untyped]
    ServiceBusClient,
    ServiceBusMessage,
)

from app.config import settings

logger = logging.getLogger('weather')


def _get_client() -> ServiceBusClient:
    """Build and return a ServiceBusClient using namespace credential or connection string."""
    if settings.azure_servicebus_namespace:
        from azure.identity import DefaultAzureCredential  # type: ignore[import-untyped]  # pylint: disable=import-outside-toplevel
        return ServiceBusClient(
            fully_qualified_namespace=settings.azure_servicebus_namespace,
            credential=DefaultAzureCredential(),  # type: ignore[arg-type]
        )
    return ServiceBusClient.from_connection_string(settings.azure_servicebus_connection_string)


def ping() -> None:
    """Verify Service Bus reachability by opening and closing a connection."""
    with _get_client() as client:
        client.get_queue_sender(settings.messaging_queue_name)


def publish(queue_name: str, body: str, message_id: str | None = None) -> None:
    """Publish a message to the named Service Bus queue (open-send-close per call)."""
    with _get_client() as client:
        with client.get_queue_sender(queue_name) as sender:
            sender.send_messages(ServiceBusMessage(body, message_id=message_id))


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
                body = str(msg)  # type: ignore[arg-type]
                try:
                    callback(body)
                    receiver.complete_message(msg)  # type: ignore[arg-type]
                except Exception:  # pylint: disable=broad-except
                    logger.exception(
                        'Service Bus message processing failed — dead-lettering: %s', body
                    )
                    receiver.dead_letter_message(msg)  # type: ignore[arg-type]
