"""MongoDB repository for pre-aggregated daily sensor stats documents."""
from datetime import date, datetime, timedelta, timezone
from typing import Any, cast

from pymongo import ASCENDING, DESCENDING

import pymongo.database
import app.infrastructure.database.mongo as _db
from app.domain.entities import DailySensorStats
from app.domain.serialization import doc_to_stats, StatsDoc
from app.domain.repositories.collections import READINGS_COLLECTION, STATS_COLLECTION

COLLECTION = STATS_COLLECTION


@_db.register_indexes
def _create_indexes(db: pymongo.database.Database[Any]) -> None:
    db[COLLECTION].create_index(
        [('sensorName', ASCENDING), ('date', DESCENDING)],
        name='sensorName_date',
    )


def count_stats(sensor_name: str) -> int:
    """Return the total number of daily stats entries for a sensor."""
    db = _db.get_database()
    return db[COLLECTION].count_documents({'sensorName': sensor_name})


def get_stats_list(
    sensor_name: str,
    skip: int = 0,
    limit: int | None = None,
) -> list[DailySensorStats]:
    """Return daily stats for a sensor ordered by date descending, with optional skip/limit."""
    db = _db.get_database()
    cursor = db[COLLECTION].find({'sensorName': sensor_name}, sort=[('date', -1)]).skip(skip)
    if limit is not None:
        cursor = cursor.limit(limit)
    return [doc_to_stats(cast(StatsDoc, doc)) for doc in cursor]


def get_daily_stats(sensor_name: str, sensor_date: date) -> DailySensorStats | None:
    """Return pre-stored daily stats for a sensor on a given date, or None if absent."""
    db = _db.get_database()
    stat_datetime = datetime(
        sensor_date.year, sensor_date.month, sensor_date.day, tzinfo=timezone.utc
    )
    doc = db[COLLECTION].find_one({'sensorName': sensor_name, 'date': stat_datetime})
    if doc is None:
        return None
    return doc_to_stats(cast(StatsDoc, doc))


def upsert_daily_stats(sensor_name: str, sensor_date: date) -> None:
    """Re-aggregate readings for sensor+day and upsert the result into weather-stats."""
    db = _db.get_database()
    start = datetime(sensor_date.year, sensor_date.month, sensor_date.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    pipeline: list[dict[str, Any]] = [
        {'$match': {'sensorName': sensor_name, 'sensorDate': {'$gte': start, '$lt': end}}},
        {'$group': {
            '_id': None,
            'count': {'$sum': 1},
            'dataInfoList': {'$push': '$dataInfo'},
        }},
    ]
    results = list(db[READINGS_COLLECTION].aggregate(pipeline))
    if not results or results[0]['count'] == 0:
        db[COLLECTION].delete_one({'sensorName': sensor_name, 'date': start})
        return

    raw = results[0]
    data_info_list = raw['dataInfoList']
    keys = {k for doc in data_info_list for k in doc if isinstance(doc[k], (int, float))}
    stats = {}
    for key in sorted(keys):
        values = [
            doc[key] for doc in data_info_list
            if key in doc and isinstance(doc[key], (int, float))
        ]
        if values:
            stats[key] = {
                'avg': round(sum(values) / len(values), 4),
                'min': min(values),
                'max': max(values),
            }

    pk = f'{sensor_name}#{sensor_date.year}'
    now = datetime.now(tz=timezone.utc)
    db[COLLECTION].update_one(
        {'pk': pk, 'sensorName': sensor_name, 'date': start},
        {
            '$set': {'pk': pk, 'sensorName': sensor_name, 'date': start,
                     'readingCount': raw['count'], 'stats': stats, 'updatedAt': now},
            '$setOnInsert': {'createdAt': now},
        },
        upsert=True,
    )
