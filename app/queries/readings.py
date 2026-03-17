"""Query objects and handlers for retrieving weather readings."""
import logging
from dataclasses import dataclass, field
from datetime import date

from app.api import mapper
from app.api.read_models import WeatherReadingDTO
from app.core.pagination import Page
from app.domain.repositories import readings as repo

logger = logging.getLogger('weather')


@dataclass
class ListReadingsQuery:
    """Query to list readings, optionally filtered by sensor name and date."""
    sensor_name: str | None
    sensor_date: date | None
    skip: int = field(default=0)
    limit: int = field(default=20)


class ListReadingsHandler:  # pylint: disable=too-few-public-methods
    """Handles ListReadingsQuery by fetching and mapping matching readings."""

    def handle(self, query: ListReadingsQuery) -> Page[WeatherReadingDTO]:
        """Execute the query and return a Page of WeatherReadingDTOs."""
        if query.sensor_name:
            logger.debug('Filtering readings by sensorName=%s', query.sensor_name)
        if query.sensor_date:
            logger.debug('Filtering readings by sensorDate=%s', query.sensor_date)
        total = repo.count_readings(sensor_name=query.sensor_name, sensor_date=query.sensor_date)
        entities = repo.list_readings(
            sensor_name=query.sensor_name,
            sensor_date=query.sensor_date,
            skip=query.skip,
            limit=query.limit,
        )
        return Page(items=[mapper.reading_to_dto(e) for e in entities], total=total)


@dataclass
class GetReadingByIdQuery:
    """Query to retrieve a single reading by sensor name and ObjectId string."""
    sensor_name: str
    reading_id: str


class GetReadingByIdHandler:  # pylint: disable=too-few-public-methods
    """Handles GetReadingByIdQuery by fetching the reading from the repository."""

    def handle(self, query: GetReadingByIdQuery) -> WeatherReadingDTO | None:
        """Return the matching DTO, or None if the reading does not exist."""
        entity = repo.get_reading_by_id(query.sensor_name, query.reading_id)
        if entity:
            logger.debug('Retrieved WeatherReading id=%s', query.reading_id)
            return mapper.reading_to_dto(entity)
        return None
