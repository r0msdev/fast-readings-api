"""Tests for the messaging layer: serialization and integration handlers."""
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import call, patch  # noqa: F401

from app.config import settings
from app.domain.events import ReadingCreated, ReadingDeleted
from app.messaging import handlers
from app.messaging.serialization import event_id, serialize


_SENSOR = 'aemet-zaorejas'
_DATE = datetime(2026, 2, 15, tzinfo=timezone.utc)
_CREATED = ReadingCreated(sensor_name=_SENSOR, sensor_date=_DATE)
_DELETED = ReadingDeleted(sensor_name=_SENSOR, sensor_date=_DATE)
_QUEUE_PATH = 'app.infrastructure.messaging.queue.publish'
_CORRELATION_PATH = 'app.messaging.serialization.get_correlation_id'


# ── serialization.serialize() ─────────────────────────────────────────────────
class SerializationTests(unittest.TestCase):
    """Wire-format contract for serialize()."""

    def test_returns_valid_json(self) -> None:
        """serialize() output must be parseable JSON."""
        body = serialize(_CREATED)
        parsed = json.loads(body)  # must not raise
        self.assertIsInstance(parsed, dict)

    def test_contains_sensor_name(self) -> None:
        body = serialize(_CREATED)
        self.assertEqual(json.loads(body)['sensorName'], _SENSOR)

    def test_contains_date_in_iso_format(self) -> None:
        body = serialize(_CREATED)
        self.assertEqual(json.loads(body)['date'], '2026-02-15')

    def test_contains_correlation_id(self) -> None:
        with patch(_CORRELATION_PATH, return_value='corr-42'):
            body = serialize(_CREATED)
        self.assertEqual(json.loads(body)['correlationId'], 'corr-42')

    def test_works_for_deleted_event(self) -> None:
        body = serialize(_DELETED)
        parsed = json.loads(body)
        self.assertEqual(parsed['sensorName'], _SENSOR)


# ── serialization.event_id() ──────────────────────────────────────────────────
class EventIdTests(unittest.TestCase):
    """Deduplication key contract for event_id()."""

    def test_format_is_sensor_colon_date(self) -> None:
        self.assertEqual(event_id(_CREATED), 'aemet-zaorejas:2026-02-15')

    def test_created_and_deleted_produce_same_key(self) -> None:
        """Same sensor+date must yield the same deduplication key regardless of event type."""
        self.assertEqual(event_id(_CREATED), event_id(_DELETED))


# ── integration handlers ───────────────────────────────────────────────────────
class OnReadingCreatedTests(unittest.TestCase):
    """on_reading_created integration handler."""

    def test_publishes_to_configured_queue(self) -> None:
        with patch(_QUEUE_PATH) as mock_publish:
            handlers.on_reading_created(_CREATED)
        mock_publish.assert_called_once()
        self.assertEqual(mock_publish.call_args[0][0], settings.messaging_queue_name)

    def test_uses_event_id_as_message_id(self) -> None:
        with patch(_QUEUE_PATH) as mock_publish:
            handlers.on_reading_created(_CREATED)
        _, kwargs = mock_publish.call_args
        self.assertEqual(kwargs['message_id'], event_id(_CREATED))

    def test_body_is_serialized_event(self) -> None:
        with patch(_QUEUE_PATH) as mock_publish, patch(_CORRELATION_PATH, return_value=''):
            handlers.on_reading_created(_CREATED)
        body = json.loads(mock_publish.call_args[0][1])
        self.assertEqual(body['sensorName'], _SENSOR)
        self.assertEqual(body['date'], '2026-02-15')


class OnReadingDeletedTests(unittest.TestCase):
    """on_reading_deleted integration handler."""

    def test_publishes_to_configured_queue(self) -> None:
        with patch(_QUEUE_PATH) as mock_publish:
            handlers.on_reading_deleted(_DELETED)
        mock_publish.assert_called_once()
        self.assertEqual(mock_publish.call_args[0][0], settings.messaging_queue_name)

    def test_uses_event_id_as_message_id(self) -> None:
        with patch(_QUEUE_PATH) as mock_publish:
            handlers.on_reading_deleted(_DELETED)
        _, kwargs = mock_publish.call_args
        self.assertEqual(kwargs['message_id'], event_id(_DELETED))


# ── publish retry ─────────────────────────────────────────────────────────────
_SLEEP_PATH = 'app.messaging.handlers.time.sleep'


class PublishRetryTests(unittest.TestCase):
    """_publish_with_retry retries on transient broker failures."""

    def test_succeeds_on_second_attempt(self) -> None:
        """A single transient failure must be recovered transparently."""
        with patch(_QUEUE_PATH, side_effect=[RuntimeError('transient'), None]) as m, \
             patch(_SLEEP_PATH):
            handlers.on_reading_created(_CREATED)
        self.assertEqual(m.call_count, 2)

    def test_raises_after_max_attempts(self) -> None:
        """Persistent failure must propagate after all retries are exhausted."""
        with patch(_QUEUE_PATH, side_effect=RuntimeError('broker down')), \
             patch(_SLEEP_PATH):
            with self.assertRaises(RuntimeError):
                handlers.on_reading_created(_CREATED)

    def test_publish_called_max_attempts_times_on_total_failure(self) -> None:
        with patch(_QUEUE_PATH, side_effect=RuntimeError('fail')) as m, \
             patch(_SLEEP_PATH):
            with self.assertRaises(RuntimeError):
                handlers.on_reading_created(_CREATED)
        self.assertEqual(m.call_count, handlers._MAX_ATTEMPTS)

    def test_sleeps_between_attempts_with_linear_backoff(self) -> None:
        """Sleep duration must scale linearly: delay×1, delay×2, … (no sleep after last attempt)."""
        with patch(_QUEUE_PATH, side_effect=RuntimeError('fail')), \
             patch(_SLEEP_PATH) as mock_sleep:
            with self.assertRaises(RuntimeError):
                handlers.on_reading_created(_CREATED)
        self.assertEqual(mock_sleep.call_count, handlers._MAX_ATTEMPTS - 1)
        mock_sleep.assert_any_call(handlers._RETRY_DELAY * 1)
        mock_sleep.assert_any_call(handlers._RETRY_DELAY * 2)

    def test_deleted_event_also_retries(self) -> None:
        """Retry applies to on_reading_deleted as well."""
        with patch(_QUEUE_PATH, side_effect=[RuntimeError('transient'), None]) as m, \
             patch(_SLEEP_PATH):
            handlers.on_reading_deleted(_DELETED)
        self.assertEqual(m.call_count, 2)


if __name__ == '__main__':
    unittest.main()


if __name__ == '__main__':
    unittest.main()
