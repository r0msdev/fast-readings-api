"""Command and handler for re-aggregating daily stats for a sensor+day."""
import logging
from dataclasses import dataclass
from datetime import date

from app.domain.repositories import stats as repo

logger = logging.getLogger('weather')


@dataclass
class RecalculateStatsCommand:
    """Command data identifying the sensor and date to re-aggregate."""

    sensor_name: str
    sensor_date: date


class RecalculateStatsHandler:  # pylint: disable=too-few-public-methods
    """Handles RecalculateStatsCommand by upserting pre-aggregated daily stats."""

    def handle(self, cmd: RecalculateStatsCommand) -> None:
        """Re-aggregate readings for sensor+day and upsert the result."""
        logger.info('Recalculating stats sensor=%s date=%s', cmd.sensor_name, cmd.sensor_date)
        repo.upsert_daily_stats(cmd.sensor_name, cmd.sensor_date)
        logger.info('Stats upserted sensor=%s date=%s', cmd.sensor_name, cmd.sensor_date)
