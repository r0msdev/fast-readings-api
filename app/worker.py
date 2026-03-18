"""Consumer worker — processes stats.recalculate messages.

Each message payload:
    {"sensorName": "...", "date": "YYYY-MM-DD", "correlationId": "..."}

On receipt the worker re-aggregates readings for that sensor+day and
upserts the result into the weather-stats collection.

Usage:
    python -m app.worker
"""
import logging
import signal
import sys

from app.config import settings
from app.domain.repositories import readings as _readings  # noqa: F401 — triggers @register_indexes  # pylint: disable=unused-import
from app.infrastructure.database.mongo import ensure_indexes
from app.infrastructure.messaging import queue
from app.messaging import consumer

logging.basicConfig(level=settings.log_level.upper())
logging.getLogger('pika').setLevel(logging.WARNING)
logger = logging.getLogger('worker')


def run() -> None:
    """Connect to the configured broker and start consuming indefinitely."""
    logger.info('Worker starting, queue=%s', settings.messaging_queue_name)
    ensure_indexes()
    from app.bootstrap import bootstrap_worker  # pylint: disable=import-outside-toplevel
    bootstrap_worker()

    def _shutdown(signum: int, _frame: object) -> None:
        logger.info('Received signal %d, shutting down', signum)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info('Worker ready, waiting for messages')
    queue.consume(settings.messaging_queue_name, consumer.handle, consumer.heartbeat)
    logger.info('Worker stopped')


if __name__ == '__main__':
    try:
        run()
    except Exception:  # pylint: disable=broad-except
        logger.exception('Worker crashed')
        sys.exit(1)
