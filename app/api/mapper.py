"""Functions that map domain entities to API response models."""
from app.api.read_models import DailySensorStatsResponse, WeatherReadingResponse
from app.domain.entities import DailySensorStats, WeatherReading


def reading_to_dto(entity: WeatherReading) -> WeatherReadingResponse:
    """Convert a WeatherReading domain entity to a WeatherReadingResponse."""
    assert entity.id is not None, 'WeatherReading must have an id before mapping to response'
    return WeatherReadingResponse(
        id=entity.id,
        sensor_name=entity.sensor_name,
        sensor_date=entity.sensor_date,
        data_info=entity.data_info,
    )


def stats_to_dto(entity: DailySensorStats) -> DailySensorStatsResponse:
    """Convert a DailySensorStats domain entity to a DailySensorStatsResponse."""
    return DailySensorStatsResponse(
        sensor_name=entity.sensor_name,
        date=entity.date,
        reading_count=entity.reading_count,
        stats=entity.stats,
    )
