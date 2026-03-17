"""Azure Service Bus messaging backend."""
# pylint: disable=import-error
import contextlib
import logging

from azure.servicebus import ServiceBusClient, ServiceBusSender, ServiceBusMessage

from app.config import settings

logger = logging.getLogger('weather')


class ServiceBusPublisher:  # pylint: disable=too-few-public-methods
    """Reusable publisher that caches one sender per queue name."""

    def __init__(self, client: ServiceBusClient) -> None:
        self.client = client
        self._senders: dict[str, ServiceBusSender] = {}

    def publish(self, queue_name: str, body: str, message_id: str | None = None) -> None:
        """Send a message to the named Service Bus queue, reusing cached senders."""
        sender = self._senders.get(queue_name)
        if sender is None or sender.is_closed:
            sender = self.client.get_queue_sender(queue_name)
            self._senders[queue_name] = sender
        sender.send_messages(ServiceBusMessage(body, message_id=message_id))


class _State:  # pylint: disable=too-few-public-methods
    publisher: ServiceBusPublisher | None = None


_state = _State()


def _get_client() -> ServiceBusClient:
    """Build and return a ServiceBusClient using namespace credential or connection string."""
    if settings.azure_servicebus_namespace:
        from azure.identity import DefaultAzureCredential  # pylint: disable=import-outside-toplevel
        return ServiceBusClient(
            fully_qualified_namespace=settings.azure_servicebus_namespace,
            credential=DefaultAzureCredential(),
        )
    return ServiceBusClient.from_connection_string(settings.azure_servicebus_connection_string)


@contextlib.contextmanager
def get_receiver(queue_name: str):
    """Context manager that yields a queue receiver for consuming messages."""
    with _get_client() as client:
        with client.get_queue_receiver(queue_name) as receiver:
            yield receiver


def ping() -> None:
    """Verify Service Bus reachability by opening and closing a connection."""
    with _get_client() as client:
        client.get_queue_sender(settings.service_bus_queue_name)


def publish(queue_name: str, body: str, message_id: str | None = None) -> None:
    """Publish a message to the named Service Bus queue."""
    if _state.publisher is None:
        _state.publisher = ServiceBusPublisher(_get_client())
    _state.publisher.publish(queue_name, body, message_id)
