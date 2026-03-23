"""Unit tests for the worker consumer path.

Covers:
  - _process(): decode JSON body and dispatch RecalculateStatsCommand
  - Debouncer: deduplication and multi-key scheduling
  - RecalculateStatsHandler: upsert delegation
"""
import json
import unittest
from datetime import date
from unittest.mock import call, patch

from app.commands.recalculate_stats import RecalculateStatsCommand, RecalculateStatsHandler
from app.core.bus import command_bus
from app.messaging import consumer
from app.messaging.consumer import Debouncer, _process


# ── _process() — command dispatch ────────────────────────────────────────────
class ProcessTests(unittest.TestCase):
    """Tests for the _process() free function."""

    def test_process_dispatches_recalculate_command(self) -> None:
        """_process should decode the JSON body and dispatch a RecalculateStatsCommand."""
        body = json.dumps({
            'sensorName': 'sensor-1',
            'date': '2026-02-15',
            'correlationId': 'abc123',
        })
        with patch.object(command_bus, 'dispatch') as mock_dispatch:
            _process(body)

        mock_dispatch.assert_called_once()
        cmd = mock_dispatch.call_args[0][0]
        self.assertIsInstance(cmd, RecalculateStatsCommand)
        self.assertEqual(cmd.sensor_name, 'sensor-1')
        self.assertEqual(cmd.sensor_date, date(2026, 2, 15))


# ── _process() — retry-with-backoff ─────────────────────────────────────────
_BODY = json.dumps({'sensorName': 'sensor-1', 'date': '2026-02-15', 'correlationId': ''})
_DISPATCH_PATH = 'app.messaging.consumer.command_bus.dispatch'
_SLEEP_PATH = 'app.messaging.consumer.time.sleep'


class ProcessRetryTests(unittest.TestCase):
    """_process() retry-with-backoff behaviour."""

    def test_succeeds_on_first_attempt_no_sleep(self) -> None:
        """No sleep when the first dispatch succeeds."""
        with patch(_DISPATCH_PATH), patch(_SLEEP_PATH) as mock_sleep:
            _process(_BODY)
        mock_sleep.assert_not_called()

    def test_retries_on_transient_failure_then_succeeds(self) -> None:
        """Retries once after a transient error and succeeds on the second attempt."""
        with (
            patch(_DISPATCH_PATH, side_effect=[RuntimeError('db down'), None]) as mock_dispatch,
            patch(_SLEEP_PATH) as mock_sleep,
        ):
            _process(_BODY)

        self.assertEqual(mock_dispatch.call_count, 2)
        mock_sleep.assert_called_once_with(consumer._RETRY_DELAY * 1)

    def test_reraises_after_all_attempts_exhausted(self) -> None:
        """After _MAX_ATTEMPTS failures _process re-raises so the broker can dead-letter."""
        with (
            patch(_DISPATCH_PATH, side_effect=RuntimeError('db permanently down')),
            patch(_SLEEP_PATH),
        ):
            with self.assertRaises(RuntimeError):
                _process(_BODY)

    def test_sleep_uses_linear_backoff(self) -> None:
        """Sleep durations increase linearly: delay*1, delay*2, …"""
        with (
            patch(_DISPATCH_PATH, side_effect=RuntimeError('fail')),
            patch(_SLEEP_PATH) as mock_sleep,
        ):
            with self.assertRaises(RuntimeError):
                _process(_BODY)

        expected = [
            call(consumer._RETRY_DELAY * attempt)
            for attempt in range(1, consumer._MAX_ATTEMPTS)
        ]
        mock_sleep.assert_has_calls(expected)

    def test_dispatch_called_max_attempts_times_on_total_failure(self) -> None:
        """Exactly _MAX_ATTEMPTS dispatch calls before giving up."""
        with (
            patch(_DISPATCH_PATH, side_effect=RuntimeError('fail')) as mock_dispatch,
            patch(_SLEEP_PATH),
        ):
            with self.assertRaises(RuntimeError):
                _process(_BODY)

        self.assertEqual(mock_dispatch.call_count, consumer._MAX_ATTEMPTS)


# ── Debouncer — deduplication ────────────────────────────────────────────────
class DebouncerTests(unittest.TestCase):
    """Tests for the Debouncer class."""

    def test_debouncer_drops_duplicate_key(self) -> None:
        """A second handle() call with the same key should be silently ignored."""
        debouncer = Debouncer(delay=60)
        try:
            body = json.dumps({'sensorName': 'sensor-1', 'date': '2026-02-15'})
            debouncer.handle(body)
            debouncer.handle(body)  # duplicate — should be dropped
            self.assertEqual(len(debouncer._timers), 1)  # pylint: disable=protected-access
        finally:
            debouncer.reset()

    def test_debouncer_allows_different_keys(self) -> None:
        """Two different sensor+date combinations should each schedule a timer."""
        debouncer = Debouncer(delay=60)
        try:
            body1 = json.dumps({'sensorName': 'sensor-1', 'date': '2026-02-15'})
            body2 = json.dumps({'sensorName': 'sensor-2', 'date': '2026-02-15'})
            debouncer.handle(body1)
            debouncer.handle(body2)
            self.assertEqual(len(debouncer._timers), 2)  # pylint: disable=protected-access
        finally:
            debouncer.reset()


# ── RecalculateStatsHandler — upsert ─────────────────────────────────────────
class RecalculateStatsHandlerTests(unittest.TestCase):
    """Tests for RecalculateStatsHandler."""

    def test_handler_calls_upsert(self) -> None:
        """handle() should delegate to repo.upsert_daily_stats with the correct args."""
        with patch('app.commands.recalculate_stats.repo.upsert_daily_stats') as mock_upsert:
            RecalculateStatsHandler().handle(
                RecalculateStatsCommand(sensor_name='sensor-1', sensor_date=date(2026, 2, 15))
            )
        mock_upsert.assert_called_once_with('sensor-1', date(2026, 2, 15))
