"""Unit tests for the worker consumer path.

Covers:
  - _process(): decode JSON body and dispatch RecalculateStatsCommand
  - Debouncer: deduplication and multi-key scheduling
  - RecalculateStatsHandler: upsert delegation
"""
import json
import unittest
from datetime import date
from unittest.mock import patch

from app.commands.recalculate_stats import RecalculateStatsCommand, RecalculateStatsHandler
from app.core.bus import command_bus
from app.messaging.consumer import Debouncer, _process


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


class RecalculateStatsHandlerTests(unittest.TestCase):
    """Tests for RecalculateStatsHandler."""

    def test_handler_calls_upsert(self) -> None:
        """handle() should delegate to repo.upsert_daily_stats with the correct args."""
        with patch('app.commands.recalculate_stats.repo.upsert_daily_stats') as mock_upsert:
            RecalculateStatsHandler().handle(
                RecalculateStatsCommand(sensor_name='sensor-1', sensor_date=date(2026, 2, 15))
            )
        mock_upsert.assert_called_once_with('sensor-1', date(2026, 2, 15))
