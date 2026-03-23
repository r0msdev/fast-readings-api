"""Command and handler for bulk-creating weather readings (207 Multi-Status)."""
import logging
from dataclasses import dataclass
from datetime import datetime

from app.api.read_models import BatchResultItem
from app.commands.create_reading import CreateReadingCommand, CreateReadingHandler
from app.core.exceptions import DuplicateResourceError

logger = logging.getLogger('weather')

_handler = CreateReadingHandler()


@dataclass
class CreateReadingsBatchCommand:
    """Command data for creating multiple readings under the same sensor."""
    sensor_name: str
    items: list[tuple[datetime, dict[str, float]]]


class CreateReadingsBatchHandler:  # pylint: disable=too-few-public-methods
    """Handles CreateReadingsBatchCommand with per-item 201/409 outcomes."""

    def handle(self, cmd: CreateReadingsBatchCommand) -> list[BatchResultItem]:
        """Attempt to create each reading independently and collect per-item outcomes.

        Returns a list of BatchResultItem with status 201 on success or 409 on duplicate.
        Other unexpected errors are re-raised immediately.
        """
        from app.api import mapper  # pylint: disable=import-outside-toplevel

        results: list[BatchResultItem] = []
        for sensor_date, data_info in cmd.items:
            try:
                entity = _handler.handle(CreateReadingCommand(
                    sensor_name=cmd.sensor_name,
                    sensor_date=sensor_date,
                    data_info=data_info,
                ))
                results.append(BatchResultItem(status=201, data=mapper.reading_to_dto(entity)))
                logger.info(
                    'Batch: created WeatherReading sensor=%s date=%s',
                    cmd.sensor_name, sensor_date,
                )
            except DuplicateResourceError as exc:
                results.append(BatchResultItem(status=409, error=str(exc)))
                logger.warning(
                    'Batch: duplicate sensor=%s date=%s', cmd.sensor_name, sensor_date,
                )
        return results
