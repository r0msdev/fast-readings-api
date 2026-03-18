"""Query objects and handlers for retrieving pre-aggregated daily sensor stats."""
import logging
from dataclasses import dataclass, field
from datetime import date

from app.api import mapper
from app.api.read_models import DailySensorStatsResponse
from app.core.exceptions import ResourceNotFoundError
from app.core.pagination import Page
from app.domain.repositories import stats as repo

logger = logging.getLogger('weather')


@dataclass
class GetStatsListQuery:
    """Query to list all daily stats entries for a sensor."""
    sensor_name: str
    skip: int = field(default=0)
    limit: int = field(default=20)


class GetStatsListHandler:  # pylint: disable=too-few-public-methods
    """Handles GetStatsListQuery by fetching and mapping stats for a sensor."""

    def handle(self, query: GetStatsListQuery) -> Page[DailySensorStatsResponse]:
        """Return a Page of DailySensorStatsResponses for the requested sensor."""
        total = repo.count_stats(query.sensor_name)
        entities = repo.get_stats_list(query.sensor_name, skip=query.skip, limit=query.limit)
        logger.debug('Listed DailySensorStats sensor=%s count=%d', query.sensor_name, total)
        return Page(items=[mapper.stats_to_dto(e) for e in entities], total=total)


@dataclass
class GetDailyStatsQuery:
    """Query to retrieve stats for a specific sensor on a specific date."""
    sensor_name: str
    date: date


class GetDailyStatsHandler:  # pylint: disable=too-few-public-methods
    """Handles GetDailyStatsQuery by fetching stats for a sensor on a given date."""

    def handle(self, query: GetDailyStatsQuery) -> DailySensorStatsResponse:
        """Return the DTO for the requested sensor+date.

        Raises ResourceNotFoundError if no stats exist for the given sensor and date.
        """
        entity = repo.get_daily_stats(query.sensor_name, query.date)
        if entity is None:
            raise ResourceNotFoundError(
                f"Stats for '{query.sensor_name}' on {query.date} not found."
            )
        logger.debug(
            'Retrieved DailySensorStats sensor=%s date=%s',
            query.sensor_name, query.date,
        )
        return mapper.stats_to_dto(entity)
