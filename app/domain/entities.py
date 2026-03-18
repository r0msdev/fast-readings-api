"""Core domain entities for the weather-readings bounded context."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class WeatherReading:
    """A single sensor measurement captured at a specific point in time."""
    sensor_name: str
    sensor_date: datetime
    data_info: dict[str, float]
    id: str | None = field(default=None)
    created_at: datetime | None = field(default=None)

    @property
    def pk(self) -> str:
        """Composite partition key in the form 'sensorName#year'."""
        return f'{self.sensor_name}#{self.sensor_date.year}'


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
