"""High-level publisher that serialises events and forwards them to the queue facade."""
import json
import logging
from datetime import datetime

from app.config import settings
from app.core.correlation import get_correlation_id
from app.infrastructure.messaging import queue

logger = logging.getLogger('weather')


def publish_reading_created(sensor_name: str, sensor_date: datetime) -> None:
    """Publish a stats-recalculation request for the given sensor and date."""
    body = json.dumps({
        'sensorName': sensor_name,
        'date': sensor_date.date().isoformat(),
        'correlationId': get_correlation_id(),
    })
    message_id = f'{sensor_name}:{sensor_date.date().isoformat()}'
    queue.publish(settings.messaging_queue_name, body, message_id)
    logger.debug('Published stats.recalculate sensor=%s date=%s', sensor_name, sensor_date.date())


def try_publish_reading_created(sensor_name: str, sensor_date: datetime) -> None:
    """Fire-and-forget wrapper: logs on failure, never raises."""
    try:
        publish_reading_created(sensor_name, sensor_date)
    except Exception:  # pylint: disable=broad-except
        logger.exception(
            'Failed to publish stats.recalculate for sensor=%s — continuing',
            sensor_name,
        )
