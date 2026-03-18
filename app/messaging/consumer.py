"""High-level consumer that deserialises events and dispatches commands."""
import json
import logging
import threading
from datetime import date
from pathlib import Path

from app.core.bus import command_bus
from app.core.correlation import set_correlation_id
from app.commands.recalculate_stats import RecalculateStatsCommand

logger = logging.getLogger('weather')

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
    """Decode a stats.recalculate message and dispatch the corresponding command."""
    payload = json.loads(body)
    sensor_name: str = payload['sensorName']
    sensor_date: date = date.fromisoformat(payload['date'])
    set_correlation_id(payload.get('correlationId', ''))
    command_bus.dispatch(RecalculateStatsCommand(sensor_name, sensor_date))


def handle(body: str) -> None:
    """Public entry point: forward to the module-level Debouncer instance."""
    _debouncer.handle(body)


def heartbeat() -> None:
    """Touch the heartbeat file so an external monitor can verify the worker is alive."""
    HEARTBEAT_FILE.touch()
