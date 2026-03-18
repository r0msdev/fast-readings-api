"""In-process message buses for commands, queries, and domain events.

Three concrete buses are exported:
  command_bus  — exactly one handler per command type; returns a value.
  query_bus    — exactly one handler per query type; returns a value.
  event_bus    — zero or more handlers per event type; returns nothing.
"""
from typing import Any, Callable


class SingleHandlerBus:
    """Dispatch bus that enforces a single handler per message type.

    Suitable for commands and queries where exactly one handler must own
    each message. Raises on duplicate registration and on unknown types.
    """

    def __init__(self) -> None:
        self._handlers: dict[type, Callable] = {}

    def register(self, message_type: type, handler_fn: Callable) -> None:
        """Associate a message type with a handler callable.

        Raises ValueError if a handler is already registered for this type.
        """
        if message_type in self._handlers:
            raise ValueError(
                f'Handler already registered for {message_type.__name__}. '
                'Use EventBus for multiple handlers per message type.'
            )
        self._handlers[message_type] = handler_fn

    def dispatch(self, message: Any) -> Any:
        """Invoke the registered handler and return its result.

        Raises ValueError if no handler is registered for the message type.
        """
        msg_type: type = type(message)
        handler = self._handlers.get(msg_type)
        if handler is None:
            raise ValueError(f'No handler registered for {msg_type.__name__}')
        return handler(message)


class EventBus:
    """Dispatch bus that supports multiple handlers per event type.

    Suitable for domain events where several listeners may react to the
    same event. Dispatching an event with no handlers registered is a no-op.
    """

    def __init__(self) -> None:
        self._handlers: dict[type, list[Callable]] = {}

    def register(self, event_type: type, handler_fn: Callable) -> None:
        """Append a handler for the given event type."""
        self._handlers.setdefault(event_type, []).append(handler_fn)

    def dispatch(self, event: Any) -> None:
        """Call all registered handlers for the event type in registration order."""
        event_type: type = type(event)
        for handler in self._handlers.get(event_type, []):
            handler(event)


command_bus = SingleHandlerBus()
query_bus = SingleHandlerBus()
event_bus = EventBus()
