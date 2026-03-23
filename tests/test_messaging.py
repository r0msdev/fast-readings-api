"""Tests for messaging event handlers — retry-with-backoff behaviour."""
import unittest
from datetime import datetime, timezone
from unittest.mock import call, patch

from app.messaging import handlers


_SENSOR = 'aemet-zaorejas'
_DATE = datetime(2026, 2, 15, tzinfo=timezone.utc)
_QUEUE_PATH = 'app.infrastructure.messaging.queue.publish'
_SLEEP_PATH = 'app.messaging.handlers.time.sleep'


class PublishReadingChangedRetryTests(unittest.TestCase):
    """publish_reading_changed retry-with-backoff behaviour."""

    def test_succeeds_on_first_attempt(self) -> None:
        """No retry and no sleep when the first publish call succeeds."""
        with (
            patch(_QUEUE_PATH) as mock_publish,
            patch(_SLEEP_PATH) as mock_sleep,
        ):
            handlers.publish_reading_changed(_SENSOR, _DATE)

        mock_publish.assert_called_once()
        mock_sleep.assert_not_called()

    def test_retries_on_transient_failure_then_succeeds(self) -> None:
        """Retries once after a transient error and succeeds on the second attempt."""
        with (
            patch(_QUEUE_PATH, side_effect=[RuntimeError('broker down'), None]) as mock_publish,
            patch(_SLEEP_PATH) as mock_sleep,
        ):
            handlers.publish_reading_changed(_SENSOR, _DATE)

        self.assertEqual(mock_publish.call_count, 2)
        mock_sleep.assert_called_once_with(handlers._RETRY_DELAY * 1)

    def test_exhausts_all_attempts_and_continues(self) -> None:
        """Logs and continues (no exception raised) when all attempts fail."""
        error = RuntimeError('broker permanently down')
        with (
            patch(_QUEUE_PATH, side_effect=error),
            patch(_SLEEP_PATH) as mock_sleep,
        ):
            # Must NOT raise
            handlers.publish_reading_changed(_SENSOR, _DATE)

        self.assertEqual(mock_sleep.call_count, handlers._MAX_ATTEMPTS - 1)

    def test_sleep_uses_linear_backoff(self) -> None:
        """Sleep durations increase linearly: delay×1, delay×2, …"""
        errors = [RuntimeError('fail')] * handlers._MAX_ATTEMPTS
        with (
            patch(_QUEUE_PATH, side_effect=errors),
            patch(_SLEEP_PATH) as mock_sleep,
        ):
            handlers.publish_reading_changed(_SENSOR, _DATE)

        expected = [
            call(handlers._RETRY_DELAY * attempt)
            for attempt in range(1, handlers._MAX_ATTEMPTS)
        ]
        mock_sleep.assert_has_calls(expected)

    def test_publish_called_max_attempts_times_on_total_failure(self) -> None:
        """Exactly _MAX_ATTEMPTS publish calls are made before giving up."""
        with (
            patch(_QUEUE_PATH, side_effect=RuntimeError('fail')),
            patch(_SLEEP_PATH),
        ):
            handlers.publish_reading_changed(_SENSOR, _DATE)

        # Checked via mock_publish — re-patch to capture
        with patch(_QUEUE_PATH, side_effect=RuntimeError('fail')) as mock_publish, \
             patch(_SLEEP_PATH):
            handlers.publish_reading_changed(_SENSOR, _DATE)

        self.assertEqual(mock_publish.call_count, handlers._MAX_ATTEMPTS)


if __name__ == '__main__':
    unittest.main()
