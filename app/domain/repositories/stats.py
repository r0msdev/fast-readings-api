"""MongoDB repository for pre-aggregated daily sensor stats documents."""
from datetime import datetime, timedelta, timezone

from pymongo import ASCENDING, DESCENDING

import app.infrastructure.database.mongo as _db
from app.domain.entities import DailySensorStats
from app.domain.serialization import doc_to_stats
from app.domain.repositories.collections import READINGS_COLLECTION, STATS_COLLECTION

COLLECTION = STATS_COLLECTION


@_db.register_indexes
def _create_indexes(db) -> None:
    db[COLLECTION].create_index(
        [('sensorName', ASCENDING), ('date', DESCENDING)],
        name='sensorName_date',
    )


def get_stats_list(sensor_name: str) -> list[DailySensorStats]:
    """Return all pre-stored daily stats for a sensor, ordered by date descending."""
    db = _db.get_database()
    docs = db[COLLECTION].find({'sensorName': sensor_name}, sort=[('date', -1)])
    return [doc_to_stats(doc) for doc in docs]


def get_daily_stats(sensor_name: str, date) -> DailySensorStats | None:
    """Return pre-stored daily stats for a sensor on a given date, or None if absent."""
    db = _db.get_database()
    stat_datetime = datetime(date.year, date.month, date.day, tzinfo=timezone.utc)
    doc = db[COLLECTION].find_one({'sensorName': sensor_name, 'date': stat_datetime})
    if doc is None:
        return None
    return doc_to_stats(doc)


def upsert_daily_stats(sensor_name: str, date) -> None:
    """Re-aggregate readings for sensor+day and upsert the result into weather-stats."""
    db = _db.get_database()
    start = datetime(date.year, date.month, date.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    pipeline = [
        {'$match': {'sensorName': sensor_name, 'sensorDate': {'$gte': start, '$lt': end}}},
        {'$group': {
            '_id': None,
            'count': {'$sum': 1},
            'dataInfoList': {'$push': '$dataInfo'},
        }},
    ]
    results = list(db[READINGS_COLLECTION].aggregate(pipeline))
    if not results or results[0]['count'] == 0:
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

    pk = f'{sensor_name}#{date.year}'
    db[COLLECTION].replace_one(
        {'pk': pk, 'sensorName': sensor_name, 'date': start},
        {'pk': pk, 'sensorName': sensor_name, 'date': start,
         'readingCount': raw['count'], 'stats': stats},
        upsert=True,
    )
