"""Event handlers — publish domain events as integration messages.

Each handler serializes the domain event and forwards it to the broker with
linear-backoff retry. If all attempts fail the exception propagates so the
caller (EventBus) can log it and the HTTP response surfaces a 5xx.
"""
import logging
import time

from app.config import settings
from app.domain.events import ReadingCreated, ReadingDeleted
from app.infrastructure.messaging import queue
from app.messaging.serialization import event_id, serialize

logger = logging.getLogger('weather')

_MAX_ATTEMPTS = 3
_RETRY_DELAY = 0.5  # seconds — linearly scaled per attempt


def _publish_with_retry(queue_name: str, body: str, message_id: str) -> None:
    """Publish to the broker, retrying up to _MAX_ATTEMPTS times on failure."""
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            queue.publish(queue_name, body, message_id=message_id)
            return
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                'Publish attempt %d/%d failed for message_id=%s — %s',
                attempt, _MAX_ATTEMPTS, message_id, exc,
            )
            if attempt < _MAX_ATTEMPTS:
                time.sleep(_RETRY_DELAY * attempt)
            else:
                raise


def on_reading_created(event: ReadingCreated) -> None:
    """Publish a stats-recalculation message for a created reading."""
    _publish_with_retry(settings.messaging_queue_name, serialize(event), event_id(event))


def on_reading_deleted(event: ReadingDeleted) -> None:
    """Publish a stats-recalculation message for a deleted reading."""
    _publish_with_retry(settings.messaging_queue_name, serialize(event), event_id(event))
