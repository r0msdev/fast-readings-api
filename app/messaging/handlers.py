"""Event handlers — react to domain events and publish integration messages."""
import json
import logging
from datetime import datetime

from app.config import settings
from app.core.correlation import get_correlation_id
from app.domain.events import ReadingCreated, ReadingDeleted
from app.infrastructure.messaging import queue

logger = logging.getLogger('weather')


def publish_reading_changed(sensor_name: str, sensor_date: datetime) -> None:
    """Publish a stats-recalculation request. Fire-and-forget — logs on failure."""
    try:
        body = json.dumps({
            'sensorName': sensor_name,
            'date': sensor_date.date().isoformat(),
            'correlationId': get_correlation_id(),
        })
        message_id = f'{sensor_name}:{sensor_date.date().isoformat()}'
        queue.publish(settings.messaging_queue_name, body, message_id)
        logger.debug(
            'Published stats.recalculate sensor=%s date=%s', sensor_name, sensor_date.date()
        )
    except Exception:  # pylint: disable=broad-except
        logger.exception(
            'Failed to publish stats.recalculate for sensor=%s — continuing',
            sensor_name,
        )


def on_reading_created(event: ReadingCreated) -> None:
    """Handle ReadingCreated: trigger stats recalculation via messaging."""
    publish_reading_changed(event.sensor_name, event.sensor_date)


def on_reading_deleted(event: ReadingDeleted) -> None:
    """Handle ReadingDeleted: trigger stats recalculation via messaging."""
    publish_reading_changed(event.sensor_name, event.sensor_date)
