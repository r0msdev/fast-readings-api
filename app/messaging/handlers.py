"""Event handlers — react to domain events and publish integration messages."""
import json
import logging
import time
from datetime import datetime

from app.config import settings
from app.core.correlation import get_correlation_id
from app.domain.events import ReadingCreated, ReadingDeleted
from app.infrastructure.messaging import queue

logger = logging.getLogger('weather')

_MAX_ATTEMPTS = 3
_RETRY_DELAY = 1.0  # seconds — linearly scaled per attempt


def publish_reading_changed(sensor_name: str, sensor_date: datetime) -> None:
    """Publish a stats-recalculation request.

    Retries up to _MAX_ATTEMPTS times with linear back-off before giving up.
    Failure is logged and silently swallowed so the HTTP response is unaffected.
    """
    body = json.dumps({
        'sensorName': sensor_name,
        'date': sensor_date.date().isoformat(),
        'correlationId': get_correlation_id(),
    })
    message_id = f'{sensor_name}:{sensor_date.date().isoformat()}'

    last_exc: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            queue.publish(settings.messaging_queue_name, body, message_id)
            logger.debug(
                'Published stats.recalculate sensor=%s date=%s', sensor_name, sensor_date.date()
            )
            return
        except Exception as exc:  # pylint: disable=broad-except
            last_exc = exc
            logger.warning(
                'Publish attempt %d/%d failed for sensor=%s — %s',
                attempt, _MAX_ATTEMPTS, sensor_name, exc,
            )
            if attempt < _MAX_ATTEMPTS:
                time.sleep(_RETRY_DELAY * attempt)

    logger.exception(
        'All %d publish attempts failed for sensor=%s — continuing',
        _MAX_ATTEMPTS, sensor_name,
        exc_info=last_exc,
    )


def on_reading_created(event: ReadingCreated) -> None:
    """Handle ReadingCreated: trigger stats recalculation via messaging."""
    publish_reading_changed(event.sensor_name, event.sensor_date)


def on_reading_deleted(event: ReadingDeleted) -> None:
    """Handle ReadingDeleted: trigger stats recalculation via messaging."""
    publish_reading_changed(event.sensor_name, event.sensor_date)
