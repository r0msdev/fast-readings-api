"""In-process message buses for commands, queries, and domain events.

Three concrete buses are exported:
  command_bus  — exactly one handler per command type; returns a value.
  query_bus    — exactly one handler per query type; returns a value.
  event_bus    — zero or more handlers per event type; returns nothing.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Protocol, runtime_checkable

logger = logging.getLogger('weather')


@runtime_checkable
class HasDomainEvents(Protocol):
    """Structural protocol satisfied by any aggregate that accumulates domain events.

    Mark entities with ``record_*`` methods and a ``collect_events()`` drain so
    the command bus can forward those events to the event bus without coupling to
    concrete types.
    """

    def collect_events(self) -> list[Any]: ...  # noqa: D102


class SingleHandlerBus:
    """Dispatch bus that enforces a single handler per message type.

    Suitable for commands and queries where exactly one handler must own
    each message. Raises on duplicate registration and on unknown types.

    Parameters
    ----------
    _event_bus:
        When supplied, any domain events accumulated on the handler's return
        value (via ``HasDomainEvents.collect_events()``) are forwarded to this
        bus immediately after the handler returns — strictly post-write.
    post_dispatch_hooks:
        Optional list of callables invoked with the handler result after event
        forwarding.  Use to attach outbox writers, structured loggers, or
        tracing spans without modifying this class.
    """

    def __init__(
        self,
        _event_bus: EventBus | None = None,
        post_dispatch_hooks: list[Callable[[Any], None]] | None = None,
    ) -> None:
        self._handlers: dict[type, Callable[..., Any]] = {}
        self.__event_bus = _event_bus
        self._post_dispatch_hooks: list[Callable[[Any], None]] = post_dispatch_hooks or []

    def register(self, message_type: type, handler_fn: Callable[..., Any]) -> None:
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

        Execution order after the handler returns:
        1. Domain events collected from the result are forwarded to the event bus.
        2. Each post-dispatch hook is called with the result.

        Raises ValueError if no handler is registered for the message type.
        """
        msg_type: type = type(message)
        handler = self._handlers.get(msg_type)
        if handler is None:
            raise ValueError(f'No handler registered for {msg_type.__name__}')
        logger.debug('Dispatching %s', msg_type.__name__)
        result: Any = handler(message)
        logger.debug('Dispatched %s → %s', msg_type.__name__, type(result).__name__)
        if self.__event_bus is not None and isinstance(result, HasDomainEvents):
            for event in result.collect_events():
                self.__event_bus.dispatch(event)
        for hook in self._post_dispatch_hooks:
            hook(result)
        return result


class EventBus:
    """Dispatch bus that supports multiple handlers per event type.

    Suitable for domain events where several listeners may react to the
    same event. Dispatching an event with no handlers registered is a no-op.
    """

    def __init__(self) -> None:
        self._handlers: dict[type, list[Callable[..., Any]]] = {}

    def register(self, event_type: type, handler_fn: Callable[..., Any]) -> None:
        """Append a handler for the given event type."""
        self._handlers.setdefault(event_type, []).append(handler_fn)

    def dispatch(self, event: Any) -> None:
        """Call all registered handlers for the event type in registration order."""
        event_type: type = type(event)
        for handler in self._handlers.get(event_type, []):
            handler(event)


event_bus = EventBus()
command_bus = SingleHandlerBus(_event_bus=event_bus)
query_bus = SingleHandlerBus()
