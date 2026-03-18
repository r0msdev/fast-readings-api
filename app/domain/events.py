"""Domain events for the weather-readings bounded context."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DomainEvent:
    """Marker base class for all domain events."""


@dataclass(frozen=True)
class ReadingCreated(DomainEvent):
    """Raised when a WeatherReading is successfully persisted."""

    sensor_name: str
    sensor_date: datetime


@dataclass(frozen=True)
class ReadingDeleted(DomainEvent):
    """Raised when a WeatherReading is removed."""

    sensor_name: str
    sensor_date: datetime
