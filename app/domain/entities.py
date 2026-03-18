"""Core domain entities for the weather-readings bounded context."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from app.domain.events import DomainEvent, ReadingCreated, ReadingDeleted


@dataclass
class WeatherReading:
    """A single sensor measurement captured at a specific point in time."""
    sensor_name: str
    sensor_date: datetime
    data_info: dict[str, float]
    id: str | None = field(default=None)
    created_at: datetime | None = field(default=None)
    _events: list[DomainEvent] = field(default_factory=list, init=False, repr=False, compare=False)

    @property
    def pk(self) -> str:
        """Composite partition key in the form 'sensorName#year'."""
        return f'{self.sensor_name}#{self.sensor_date.year}'

    def record_created(self) -> None:
        """Record a ReadingCreated domain event."""
        self._events.append(ReadingCreated(self.sensor_name, self.sensor_date))

    def record_deleted(self) -> None:
        """Record a ReadingDeleted domain event."""
        self._events.append(ReadingDeleted(self.sensor_name, self.sensor_date))

    def collect_events(self) -> list[DomainEvent]:
        """Drain and return all pending domain events."""
        events, self._events = self._events, []
        return events


@dataclass
class DailySensorStats:
    """Pre-aggregated statistics for one sensor over a calendar day."""
    sensor_name: str
    date: date
    reading_count: int
    stats: dict[str, dict[str, float]]
    created_at: datetime | None = field(default=None)
    updated_at: datetime | None = field(default=None)

    @property
    def pk(self) -> str:
        """Composite partition key in the form 'sensorName#year'."""
        return f'{self.sensor_name}#{self.date.year}'
