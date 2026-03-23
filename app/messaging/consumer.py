"""High-level consumer that deserialises events and dispatches commands."""
import json
import logging
import threading
import time
from datetime import date
from pathlib import Path

from app.core.bus import command_bus
from app.core.correlation import set_correlation_id
from app.commands.recalculate_stats import RecalculateStatsCommand

logger = logging.getLogger('weather')

_MAX_ATTEMPTS = 3
_RETRY_DELAY = 1.0  # seconds — linearly scaled per attempt

HEARTBEAT_FILE = Path('/tmp/worker.heartbeat')
DEBOUNCE_DELAY = 15  # seconds


class Debouncer:
    """Leading-edge debounce for sensor+date keys.

    The first message for a given key schedules _process after DEBOUNCE_DELAY
    seconds; duplicate messages within that window are silently dropped so rapid
    bursts produce only one DB upsert. Encapsulating state in a class makes the
    timer dict resettable in tests without relying on module reload.
    """

    def __init__(self, delay: float = DEBOUNCE_DELAY) -> None:
        self._delay = delay
        self._timers: dict[str, threading.Timer] = {}

    def handle(self, body: str) -> None:
        """Schedule _process for the decoded key, discarding duplicates."""
        payload = json.loads(body)
        key = f"{payload['sensorName']}:{payload['date']}"
        if key in self._timers:
            logger.debug('Debounced key=%s', key)
            return

        def _fire(b: str = body, k: str = key) -> None:
            self._timers.pop(k, None)
            _process(b)

        t = threading.Timer(self._delay, _fire)
        self._timers[key] = t
        t.start()
        logger.debug('Debounce scheduled key=%s', key)

    def reset(self) -> None:
        """Cancel all pending timers and clear state — intended for tests."""
        for t in self._timers.values():
            t.cancel()
        self._timers.clear()


_debouncer = Debouncer()


def _process(body: str) -> None:
    """Decode a stats.recalculate message and dispatch the corresponding command.

    Retries up to _MAX_ATTEMPTS times with linear back-off. On total failure the
    exception propagates so the broker can nack/dead-letter the message.
    """
    payload = json.loads(body)
    sensor_name: str = payload['sensorName']
    sensor_date: date = date.fromisoformat(payload['date'])
    set_correlation_id(payload.get('correlationId', ''))
    cmd = RecalculateStatsCommand(sensor_name, sensor_date)

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            command_bus.dispatch(cmd)
            return
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                'Process attempt %d/%d failed for sensor=%s — %s',
                attempt, _MAX_ATTEMPTS, sensor_name, exc,
            )
            if attempt < _MAX_ATTEMPTS:
                time.sleep(_RETRY_DELAY * attempt)
            else:
                raise  # nack → dead-letter queue


def handle(body: str) -> None:
    """Public entry point: forward to the module-level Debouncer instance."""
    _debouncer.handle(body)


def heartbeat() -> None:
    """Touch the heartbeat file so an external monitor can verify the worker is alive."""
    HEARTBEAT_FILE.touch()
