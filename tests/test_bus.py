"""Unit tests for app/core/bus.py — SingleHandlerBus, EventBus, HasDomainEvents."""
from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import MagicMock

import pytest

from app.core.bus import EventBus, HasDomainEvents, SingleHandlerBus


# ── Test doubles ────────────────────────────────────────────────────────────

@dataclass
class _Cmd:
    value: int


@dataclass
class _OtherCmd:
    value: str


@dataclass
class _FakeEvent:
    name: str


@dataclass
class _AggregateResult:
    """Satisfies HasDomainEvents — mimics a domain entity with pending events."""
    _pending: list[_FakeEvent] = field(default_factory=list, init=False)

    def add_event(self, e: _FakeEvent) -> None:
        self._pending.append(e)

    def collect_events(self) -> list[_FakeEvent]:
        events, self._pending = self._pending, []
        return events


@dataclass
class _PlainResult:
    """Does NOT satisfy HasDomainEvents — no collect_events()."""
    value: int


# ── HasDomainEvents Protocol ────────────────────────────────────────────────

class TestHasDomainEventsProtocol:
    def test_aggregate_satisfies_protocol(self) -> None:
        assert isinstance(_AggregateResult(), HasDomainEvents)

    def test_plain_object_does_not_satisfy_protocol(self) -> None:
        assert not isinstance(_PlainResult(1), HasDomainEvents)

    def test_string_does_not_satisfy_protocol(self) -> None:
        assert not isinstance("hello", HasDomainEvents)


# ── SingleHandlerBus — registration ─────────────────────────────────────────

class TestSingleHandlerBusRegistration:
    def test_register_and_dispatch_returns_handler_result(self) -> None:
        bus = SingleHandlerBus()
        bus.register(_Cmd, lambda cmd: cmd.value * 2)
        assert bus.dispatch(_Cmd(value=5)) == 10

    def test_duplicate_registration_raises(self) -> None:
        bus = SingleHandlerBus()
        bus.register(_Cmd, lambda cmd: None)
        with pytest.raises(ValueError, match='Handler already registered'):
            bus.register(_Cmd, lambda cmd: None)

    def test_unknown_message_type_raises(self) -> None:
        bus = SingleHandlerBus()
        with pytest.raises(ValueError, match='No handler registered'):
            bus.dispatch(_Cmd(value=1))

    def test_multiple_distinct_types_registered(self) -> None:
        bus = SingleHandlerBus()
        bus.register(_Cmd, lambda cmd: cmd.value + 1)
        bus.register(_OtherCmd, lambda cmd: cmd.value.upper())
        assert bus.dispatch(_Cmd(value=3)) == 4
        assert bus.dispatch(_OtherCmd(value='hi')) == 'HI'


# ── SingleHandlerBus — event forwarding via HasDomainEvents ─────────────────

class TestSingleHandlerBusEventForwarding:
    def test_events_forwarded_to_event_bus_after_handler(self) -> None:
        event_bus = EventBus()
        received: list[_FakeEvent] = []
        event_bus.register(_FakeEvent, received.append)

        def handler(cmd: _Cmd) -> _AggregateResult:
            agg = _AggregateResult()
            agg.add_event(_FakeEvent(name='created'))
            return agg

        bus = SingleHandlerBus(_event_bus=event_bus)
        bus.register(_Cmd, handler)
        bus.dispatch(_Cmd(value=1))

        assert len(received) == 1
        assert received[0].name == 'created'

    def test_multiple_events_all_forwarded(self) -> None:
        event_bus = EventBus()
        received: list[_FakeEvent] = []
        event_bus.register(_FakeEvent, received.append)

        def handler(cmd: _Cmd) -> _AggregateResult:
            agg = _AggregateResult()
            agg.add_event(_FakeEvent(name='a'))
            agg.add_event(_FakeEvent(name='b'))
            return agg

        bus = SingleHandlerBus(_event_bus=event_bus)
        bus.register(_Cmd, handler)
        bus.dispatch(_Cmd(value=1))

        assert [e.name for e in received] == ['a', 'b']

    def test_no_events_forwarded_when_result_has_no_collect_events(self) -> None:
        event_bus = EventBus()
        handler_mock = MagicMock()
        event_bus.register(_FakeEvent, handler_mock)

        bus = SingleHandlerBus(_event_bus=event_bus)
        bus.register(_Cmd, lambda cmd: _PlainResult(value=99))
        bus.dispatch(_Cmd(value=1))

        handler_mock.assert_not_called()

    def test_no_event_bus_wired_does_not_raise(self) -> None:
        def handler(cmd: _Cmd) -> _AggregateResult:
            agg = _AggregateResult()
            agg.add_event(_FakeEvent(name='x'))
            return agg

        bus = SingleHandlerBus()  # no _event_bus
        bus.register(_Cmd, handler)
        bus.dispatch(_Cmd(value=1))  # must not raise

    def test_collect_events_drained_after_dispatch(self) -> None:
        """collect_events() must drain the aggregate so a second dispatch emits nothing."""
        event_bus = EventBus()
        received: list[_FakeEvent] = []
        event_bus.register(_FakeEvent, received.append)

        agg = _AggregateResult()
        agg.add_event(_FakeEvent(name='once'))

        bus = SingleHandlerBus(_event_bus=event_bus)
        bus.register(_Cmd, lambda cmd: agg)
        bus.dispatch(_Cmd(value=1))
        bus.dispatch(_Cmd(value=2))

        assert len(received) == 1  # second dispatch produces no new events


# ── SingleHandlerBus — post-dispatch hooks ───────────────────────────────────

class TestSingleHandlerBusHooks:
    def test_single_hook_called_with_result(self) -> None:
        hook = MagicMock()
        bus = SingleHandlerBus(post_dispatch_hooks=[hook])
        bus.register(_Cmd, lambda cmd: _PlainResult(value=7))
        result = bus.dispatch(_Cmd(value=1))

        hook.assert_called_once_with(result)

    def test_multiple_hooks_called_in_order(self) -> None:
        call_order: list[str] = []
        bus = SingleHandlerBus(post_dispatch_hooks=[
            lambda r: call_order.append('first'),
            lambda r: call_order.append('second'),
        ])
        bus.register(_Cmd, lambda cmd: _PlainResult(value=0))
        bus.dispatch(_Cmd(value=1))

        assert call_order == ['first', 'second']

    def test_hooks_fire_after_event_forwarding(self) -> None:
        """Events must reach the event bus before hooks run."""
        call_log: list[str] = []
        event_bus = EventBus()
        event_bus.register(_FakeEvent, lambda e: call_log.append('event'))

        def handler(cmd: _Cmd) -> _AggregateResult:
            agg = _AggregateResult()
            agg.add_event(_FakeEvent(name='x'))
            return agg

        bus = SingleHandlerBus(
            _event_bus=event_bus,
            post_dispatch_hooks=[lambda r: call_log.append('hook')],
        )
        bus.register(_Cmd, handler)
        bus.dispatch(_Cmd(value=1))

        assert call_log == ['event', 'hook']

    def test_no_hooks_by_default(self) -> None:
        """Constructing without hooks must not raise and must return result normally."""
        bus = SingleHandlerBus()
        bus.register(_Cmd, lambda cmd: _PlainResult(value=42))
        assert bus.dispatch(_Cmd(value=1)) == _PlainResult(value=42)


# ── EventBus ─────────────────────────────────────────────────────────────────

class TestEventBus:
    def test_single_handler_called(self) -> None:
        bus = EventBus()
        received: list[_FakeEvent] = []
        bus.register(_FakeEvent, received.append)
        bus.dispatch(_FakeEvent(name='x'))

        assert received == [_FakeEvent(name='x')]

    def test_multiple_handlers_called_in_registration_order(self) -> None:
        bus = EventBus()
        call_order: list[int] = []
        bus.register(_FakeEvent, lambda e: call_order.append(1))
        bus.register(_FakeEvent, lambda e: call_order.append(2))
        bus.dispatch(_FakeEvent(name='y'))

        assert call_order == [1, 2]

    def test_dispatch_with_no_handlers_is_noop(self) -> None:
        bus = EventBus()
        bus.dispatch(_FakeEvent(name='z'))  # must not raise

    def test_handlers_isolated_by_event_type(self) -> None:
        @dataclass
        class _OtherEvent:
            value: int

        bus = EventBus()
        received_fake: list[_FakeEvent] = []
        received_other: list[_OtherEvent] = []
        bus.register(_FakeEvent, received_fake.append)
        bus.register(_OtherEvent, received_other.append)

        bus.dispatch(_FakeEvent(name='a'))
        bus.dispatch(_OtherEvent(value=9))

        assert len(received_fake) == 1
        assert len(received_other) == 1


# ── Debug logging ────────────────────────────────────────────────────────────

class TestSingleHandlerBusLogging:
    def test_debug_messages_emitted(self, caplog: pytest.LogCaptureFixture) -> None:
        import logging
        bus = SingleHandlerBus()
        bus.register(_Cmd, lambda cmd: _PlainResult(value=0))

        with caplog.at_level(logging.DEBUG, logger='weather'):
            bus.dispatch(_Cmd(value=1))

        messages = [r.message for r in caplog.records]
        assert any('Dispatching' in m and '_Cmd' in m for m in messages)
        assert any('Dispatched' in m and '_Cmd' in m for m in messages)
