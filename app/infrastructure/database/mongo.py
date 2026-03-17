"""MongoDB client and index-registration helpers."""
import logging
import warnings
from functools import lru_cache
from typing import Callable

import pymongo

from app.config import settings

logger = logging.getLogger('core')

_index_registrations: list[Callable[[pymongo.database.Database], None]] = []


def register_indexes(fn: Callable[[pymongo.database.Database], None]) -> Callable:
    """Decorator that registers a function to create indexes for one collection."""
    _index_registrations.append(fn)
    return fn


def ensure_indexes() -> None:
    """Run all registered index creation functions. Safe to call on every startup."""
    db = get_database()
    for fn in _index_registrations:
        fn(db)
    logger.info('MongoDB indexes ensured (%d registrations)', len(_index_registrations))


@lru_cache(maxsize=None)
def _get_client() -> pymongo.MongoClient:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            'ignore', message='You appear to be connected to a CosmosDB cluster'
        )
        return pymongo.MongoClient(settings.mongodb_uri)


def get_database() -> pymongo.database.Database:
    """Return the configured MongoDB database."""
    return _get_client()[settings.mongodb_db_name]


def reset_client() -> None:
    """Clear the cached client — used in tests to reset state."""
    _get_client.cache_clear()
