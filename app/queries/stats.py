"""Query objects and handlers for retrieving pre-aggregated daily sensor stats."""
import logging
from dataclasses import dataclass
from datetime import date

from app.api import mapper
from app.api.read_models import DailySensorStatsDTO
from app.domain.repositories import stats as repo

logger = logging.getLogger('weather')


@dataclass
class GetStatsListQuery:
    """Query to list all daily stats entries for a sensor."""
    sensor_name: str


class GetStatsListHandler:  # pylint: disable=too-few-public-methods
    """Handles GetStatsListQuery by fetching and mapping all stats for a sensor."""

    def handle(self, query: GetStatsListQuery) -> list[DailySensorStatsDTO]:
        """Return all DailySensorStatsDTOs for the requested sensor."""
        entities = repo.get_stats_list(query.sensor_name)
        logger.debug('Listed DailySensorStats sensor=%s count=%d', query.sensor_name, len(entities))
        return [mapper.stats_to_dto(e) for e in entities]


@dataclass
class GetDailyStatsQuery:
    """Query to retrieve stats for a specific sensor on a specific date."""
    sensor_name: str
    date: date


class GetDailyStatsHandler:  # pylint: disable=too-few-public-methods
    """Handles GetDailyStatsQuery by fetching stats for a sensor on a given date."""

    def handle(self, query: GetDailyStatsQuery) -> DailySensorStatsDTO | None:
        """Return the DTO for the requested sensor+date, or None if absent."""
        entity = repo.get_daily_stats(query.sensor_name, query.date)
        if entity:
            logger.debug(
                'Retrieved DailySensorStats sensor=%s date=%s',
                query.sensor_name, query.date,
            )
            return mapper.stats_to_dto(entity)
        return None
