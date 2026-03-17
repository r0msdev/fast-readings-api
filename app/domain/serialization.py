"""Serialization helpers that map between MongoDB documents and domain entities."""
from datetime import datetime, timezone
from datetime import date as _date
from typing import TypedDict

from app.domain.entities import DailySensorStats, WeatherReading


class NewReadingDoc(TypedDict):
    """Shape of a readings document before insertion (no _id yet)."""
    pk: str
    sensorName: str
    sensorDate: datetime
    dataInfo: dict[str, float]
    createdAt: datetime


class ReadingDoc(NewReadingDoc):
    """Shape of a MongoDB document in the readings collection (after insertion)."""
    _id: object


class StatsDoc(TypedDict):
    """Shape of a MongoDB document in the weather-stats collection."""
    pk: str
    sensorName: str
    date: datetime | str
    readingCount: int
    stats: dict[str, dict[str, float]]


def doc_to_reading(doc: ReadingDoc) -> WeatherReading:
    """Map a MongoDB document to a WeatherReading domain object."""
    return WeatherReading(
        id=str(doc['_id']),
        sensor_name=doc['sensorName'],
        sensor_date=doc['sensorDate'],
        data_info=doc['dataInfo'],
    )


def reading_to_doc(entity: WeatherReading) -> NewReadingDoc:
    """Map a WeatherReading entity to a MongoDB document ready for insertion."""
    return {
        'pk': entity.pk,
        'sensorName': entity.sensor_name,
        'sensorDate': entity.sensor_date,
        'dataInfo': entity.data_info,
        'createdAt': datetime.now(tz=timezone.utc),
    }


def doc_to_stats(doc: StatsDoc) -> DailySensorStats:
    """Map a weather-stats MongoDB document to a DailySensorStats domain object."""
    raw_date = doc['date']
    stat_date = raw_date.date() if isinstance(raw_date, datetime) else _date.fromisoformat(raw_date)
    return DailySensorStats(
        sensor_name=doc['sensorName'],
        date=stat_date,
        reading_count=doc['readingCount'],
        stats=doc['stats'],
    )
