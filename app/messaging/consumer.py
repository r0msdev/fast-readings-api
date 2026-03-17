"""High-level consumer that deserialises events and delegates to domain logic."""
import json
import logging
from datetime import date

from app.core.correlation import set_correlation_id
from app.domain.repositories import stats as stats_repo

logger = logging.getLogger('weather')


def handle(body: str) -> None:
    """Decode and process a single stats.recalculate message."""
    payload = json.loads(body)
    sensor_name: str = payload['sensorName']
    sensor_date: date = date.fromisoformat(payload['date'])
    set_correlation_id(payload.get('correlationId', ''))
    logger.info('Recalculating stats sensor=%s date=%s', sensor_name, sensor_date)
    stats_repo.upsert_daily_stats(sensor_name, sensor_date)
    logger.info('Stats upserted sensor=%s date=%s', sensor_name, sensor_date)
