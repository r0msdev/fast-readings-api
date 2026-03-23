"""Wire-format serialization for reading domain events.

These pure functions define the integration contract between the API publisher
and the worker consumer. Both ends must stay in sync with the same field names.
"""
import json

from app.core.correlation import get_correlation_id
from app.domain.events import ReadingCreated, ReadingDeleted


def serialize(event: ReadingCreated | ReadingDeleted) -> str:
    """Serialize a reading domain event to the integration wire format (JSON string)."""
    return json.dumps({
        'sensorName': event.sensor_name,
        'date': event.sensor_date.date().isoformat(),
        'correlationId': get_correlation_id(),
    })


def event_id(event: ReadingCreated | ReadingDeleted) -> str:
    """Stable deduplication key derived from the event identity."""
    return f'{event.sensor_name}:{event.sensor_date.date().isoformat()}'
