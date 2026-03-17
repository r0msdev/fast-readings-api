"""In-process message bus for dispatching commands and queries to handlers."""
from typing import Any, Callable


class MessageBus:
    """Maps message types to handler callables and dispatches messages to them."""

    def __init__(self) -> None:
        self._handlers: dict[type, Callable] = {}

    def register(self, message_type: type, handler_fn: Callable) -> None:
        """Associate a message type with a handler callable."""
        self._handlers[message_type] = handler_fn

    def dispatch(self, message: Any) -> Any:
        """Find the registered handler for the message type and invoke it."""
        handler = self._handlers.get(type(message))
        if handler is None:
            raise ValueError(f'No handler registered for {type(message).__name__}')
        return handler(message)


command_bus = MessageBus()
query_bus = MessageBus()
