"""MongoDB repository for weather reading documents."""
from datetime import date, datetime, timedelta, timezone
from typing import Any, cast

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ASCENDING, DESCENDING

import pymongo.database
import app.infrastructure.database.mongo as _db
from app.domain.serialization import reading_to_doc, doc_to_reading, ReadingDoc
from app.domain.entities import WeatherReading
from app.domain.repositories.collections import READINGS_COLLECTION

COLLECTION = READINGS_COLLECTION


@_db.register_indexes
def _create_indexes(db: pymongo.database.Database[Any]) -> None:
    db[COLLECTION].create_index(
        [('sensorName', ASCENDING), ('sensorDate', DESCENDING)],
        name='sensorName_sensorDate',
    )


def list_readings(
    sensor_name: str | None = None,
    sensor_date: date | None = None,
    skip: int = 0,
    limit: int | None = None,
) -> list[WeatherReading]:
    """Return readings sorted by sensorDate descending, optionally filtered and paginated."""
    db = _db.get_database()
    query = {}
    if sensor_name:
        query['sensorName'] = sensor_name
    if sensor_date:
        start = datetime(sensor_date.year, sensor_date.month, sensor_date.day, tzinfo=timezone.utc)
        query['sensorDate'] = {'$gte': start, '$lt': start + timedelta(days=1)}
    cursor = db[COLLECTION].find(query).sort('sensorDate', -1).skip(skip)
    if limit is not None:
        cursor = cursor.limit(limit)
    return [doc_to_reading(cast(ReadingDoc, doc)) for doc in cursor]


def count_readings(
    sensor_name: str | None = None,
    sensor_date: date | None = None,
) -> int:
    """Return the total number of readings matching the given filters."""
    db = _db.get_database()
    query: dict[str, object] = {}
    if sensor_name:
        query['sensorName'] = sensor_name
    if sensor_date:
        start = datetime(sensor_date.year, sensor_date.month, sensor_date.day, tzinfo=timezone.utc)
        query['sensorDate'] = {'$gte': start, '$lt': start + timedelta(days=1)}
    return db[COLLECTION].count_documents(query)


def reading_exists(sensor_name: str, sensor_date: datetime) -> bool:
    """Return True if a reading with the same sensorName and sensorDate already exists."""
    db = _db.get_database()
    return db[COLLECTION].count_documents(
        {'sensorName': sensor_name, 'sensorDate': sensor_date}, limit=1
    ) > 0


def create_reading(entity: WeatherReading) -> WeatherReading:
    """Persist a new WeatherReading and return the domain object."""
    db = _db.get_database()
    doc = reading_to_doc(entity)
    result = db[COLLECTION].insert_one(doc)
    full_doc: ReadingDoc = {**doc, '_id': result.inserted_id}
    return doc_to_reading(full_doc)


def get_reading_by_id(sensor_name: str, reading_id: str) -> WeatherReading | None:
    """Return a single WeatherReading by sensorName and ObjectId hex string, or None."""
    db = _db.get_database()
    try:
        oid = ObjectId(reading_id)
    except InvalidId:
        return None
    doc = db[COLLECTION].find_one({'_id': oid, 'sensorName': sensor_name})
    return doc_to_reading(cast(ReadingDoc, doc)) if doc is not None else None


def delete_reading(sensor_name: str, reading_id: str) -> WeatherReading | None:
    """Delete a reading by sensorName and ObjectId hex string.

    Returns the deleted WeatherReading, or None if the document did not exist.
    Uses find_one_and_delete for a single atomic round-trip.
    """
    db = _db.get_database()
    try:
        oid = ObjectId(reading_id)
    except InvalidId:
        return None
    doc = db[COLLECTION].find_one_and_delete({'_id': oid, 'sensorName': sensor_name})
    return doc_to_reading(cast(ReadingDoc, doc)) if doc is not None else None
