"""Functions that map domain entities to API DTOs."""
from app.api.read_models import DailySensorStatsDTO, WeatherReadingDTO
from app.domain.entities import DailySensorStats, WeatherReading


def reading_to_dto(entity: WeatherReading) -> WeatherReadingDTO:
    """Convert a WeatherReading domain entity to a WeatherReadingDTO."""
    assert entity.id is not None, 'WeatherReading must have an id before mapping to DTO'
    return WeatherReadingDTO(
        id=entity.id,
        sensor_name=entity.sensor_name,
        sensor_date=entity.sensor_date,
        data_info=entity.data_info,
    )


def stats_to_dto(entity: DailySensorStats) -> DailySensorStatsDTO:
    """Convert a DailySensorStats domain entity to a DailySensorStatsDTO."""
    return DailySensorStatsDTO(
        sensor_name=entity.sensor_name,
        date=entity.date,
        reading_count=entity.reading_count,
        stats=entity.stats,
    )
