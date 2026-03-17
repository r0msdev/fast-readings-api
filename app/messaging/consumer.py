"""High-level consumer that deserialises events and delegates to domain logic."""
import json
import logging
import threading
from datetime import date
from pathlib import Path

from app.core.correlation import set_correlation_id
from app.domain.repositories import stats as stats_repo

logger = logging.getLogger('weather')

HEARTBEAT_FILE = Path('/tmp/worker.heartbeat')
DEBOUNCE_DELAY = 15  # seconds

_timers: dict[str, threading.Timer] = {}


def _process(body: str) -> None:
    """Decode and process a single stats.recalculate message."""
    payload = json.loads(body)
    sensor_name: str = payload['sensorName']
    sensor_date: date = date.fromisoformat(payload['date'])
    set_correlation_id(payload.get('correlationId', ''))
    logger.info('Recalculating stats sensor=%s date=%s', sensor_name, sensor_date)
    stats_repo.upsert_daily_stats(sensor_name, sensor_date)
    logger.info('Stats upserted sensor=%s date=%s', sensor_name, sensor_date)


def handle(body: str) -> None:
    """Leading-edge debounce: first message for a sensor+date key schedules
    _process after DEBOUNCE_DELAY seconds; duplicates within that window are
    discarded so rapid bursts produce only one DB upsert.
    """
    payload = json.loads(body)
    key = f"{payload['sensorName']}:{payload['date']}"
    if key in _timers:
        logger.debug('Debounced key=%s', key)
        return

    def _fire(b: str = body, k: str = key) -> None:
        _timers.pop(k, None)
        _process(b)

    t = threading.Timer(DEBOUNCE_DELAY, _fire)
    _timers[key] = t
    t.start()
    logger.debug('Debounce scheduled key=%s', key)


def heartbeat() -> None:
    """Touch the heartbeat file so an external monitor can verify the worker is alive."""
    HEARTBEAT_FILE.touch()
