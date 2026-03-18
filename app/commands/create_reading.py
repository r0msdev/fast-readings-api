"""Command and handler for creating a new weather reading."""
import logging
from dataclasses import dataclass
from datetime import datetime

from app.api import mapper
from app.api.read_models import WeatherReadingResponse
from app.domain.entities import WeatherReading
from app.domain.repositories import readings as repo
from app.messaging import publisher
from app.core.exceptions import DuplicateResourceError

logger = logging.getLogger('weather')


@dataclass
class CreateReadingCommand:
    """Command data for creating a reading for the given sensor and date."""
    sensor_name: str
    sensor_date: datetime
    data_info: dict[str, float]


class CreateReadingHandler:  # pylint: disable=too-few-public-methods
    """Handles CreateReadingCommand by persisting the reading and publishing an event."""

    def handle(self, cmd: CreateReadingCommand) -> WeatherReadingResponse:
        """Persist a new reading and publish a stats recalculation event.

        Raises DuplicateResourceError if a reading with the same sensorName
        and sensorDate already exists.
        """
        if repo.reading_exists(cmd.sensor_name, cmd.sensor_date):
            raise DuplicateResourceError(
                f"A reading for '{cmd.sensor_name}' at {cmd.sensor_date} already exists."
            )
        entity = repo.create_reading(WeatherReading(
            sensor_name=cmd.sensor_name,
            sensor_date=cmd.sensor_date,
            data_info=cmd.data_info,
        ))
        logger.info('Created WeatherReading id=%s sensor=%s', entity.id, entity.sensor_name)
        publisher.try_publish_reading_created(entity.sensor_name, entity.sensor_date)
        return mapper.reading_to_dto(entity)
