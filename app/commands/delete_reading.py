"""Command and handler for deleting an existing weather reading."""
import logging
from dataclasses import dataclass

from app.domain.repositories import readings as repo
from app.messaging import publisher

logger = logging.getLogger('weather')


@dataclass
class DeleteReadingCommand:
    """Command data identifying the reading to delete by sensor name and ID."""
    sensor_name: str
    reading_id: str


class DeleteReadingHandler:  # pylint: disable=too-few-public-methods
    """Handles DeleteReadingCommand by removing the reading and publishing an event."""

    def handle(self, cmd: DeleteReadingCommand) -> bool:
        """Delete a reading scoped to a sensor.

        Returns True if the reading was deleted, False if it did not exist.
        Publishes stats.recalculate when a reading is successfully deleted.
        """
        reading = repo.delete_reading(cmd.sensor_name, cmd.reading_id)
        if reading is None:
            return False
        logger.info('Deleted WeatherReading id=%s sensor=%s', cmd.reading_id, cmd.sensor_name)
        publisher.try_publish_reading_created(reading.sensor_name, reading.sensor_date)
        return True
