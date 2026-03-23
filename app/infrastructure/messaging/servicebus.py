"""Azure Service Bus messaging backend."""
# pylint: disable=import-error
import logging
from collections.abc import Callable
from threading import Lock

from azure.servicebus import (  # type: ignore[import-untyped]
    ServiceBusClient,
    ServiceBusSender,
    ServiceBusMessage,
)
from azure.servicebus.exceptions import ServiceBusError  # type: ignore[import-untyped]

from app.config import settings

logger = logging.getLogger('weather')


def _build_client() -> ServiceBusClient:
    """Build a ServiceBusClient using namespace credential or connection string."""
    if settings.azure_servicebus_namespace:
        from azure.identity import DefaultAzureCredential  # type: ignore[import-untyped]  # pylint: disable=import-outside-toplevel
        return ServiceBusClient(
            fully_qualified_namespace=settings.azure_servicebus_namespace,
            credential=DefaultAzureCredential(),  # type: ignore[arg-type]
        )
    return ServiceBusClient.from_connection_string(settings.azure_servicebus_connection_string)


class ServiceBusSenderPool:
    """Thread-safe pool that lazily creates a shared client and caches per-queue senders."""

    def __init__(self) -> None:
        self._client: ServiceBusClient | None = None
        self._senders: dict[str, ServiceBusSender] = {}
        self._lock = Lock()

    def get_sender(self, queue_name: str) -> ServiceBusSender:
        """Return a cached sender, lazily creating the shared client on first use."""
        with self._lock:
            if self._client is None:
                self._client = _build_client()
            if queue_name not in self._senders:
                sender = self._client.get_queue_sender(queue_name)  # type: ignore[union-attr]
                self._senders[queue_name] = sender
            return self._senders[queue_name]

    def evict(self, queue_name: str) -> None:
        """Remove a stale sender so the next call to get_sender() recreates it."""
        with self._lock:
            self._senders.pop(queue_name, None)

    def close(self) -> None:
        """Close all cached senders and the shared client, resetting the pool."""
        with self._lock:
            for sender in self._senders.values():
                try:
                    sender.close()
                except Exception:  # pylint: disable=broad-except
                    logger.debug('Error closing sender', exc_info=True)
            self._senders.clear()

            if self._client:
                try:
                    self._client.close()
                except Exception:  # pylint: disable=broad-except
                    logger.debug('Error closing Service Bus client', exc_info=True)
                self._client = None


_pool = ServiceBusSenderPool()


def close() -> None:
    """Release all cached senders and the shared client."""
    _pool.close()


def ping() -> None:
    """Verify Service Bus reachability by opening and closing a connection."""
    with _build_client() as client:
        client.get_queue_sender(settings.messaging_queue_name)


def publish(queue_name: str, body: str, message_id: str | None = None) -> None:
    """Publish a message, reusing a cached sender. Retries once on a stale connection."""
    for attempt in range(2):
        try:
            sender = _pool.get_sender(queue_name)
            sender.send_messages(ServiceBusMessage(body, message_id=message_id))
            return
        except ServiceBusError:
            if attempt == 0:
                _pool.evict(queue_name)  # evict stale sender and retry
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
    with _build_client() as client:
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
