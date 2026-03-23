"""Pydantic DTOs returned by the API layer."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class WeatherReadingResponse(BaseModel):
    """Read model for a single sensor reading returned by the API."""
    model_config = ConfigDict(populate_by_name=True)

    id: str
    sensor_name: str = Field(serialization_alias='sensorName')
    sensor_date: datetime = Field(serialization_alias='sensorDate')
    data_info: dict[str, float] = Field(serialization_alias='dataInfo')


class DailySensorStatsResponse(BaseModel):
    """Read model for pre-aggregated daily stats for one sensor."""
    model_config = ConfigDict(populate_by_name=True)

    sensor_name: str = Field(serialization_alias='sensorName')
    date: date
    reading_count: int = Field(serialization_alias='readingCount')
    stats: dict[str, dict[str, float]]


class BatchResultItem(BaseModel):
    """Per-item outcome in a bulk-create 207 response."""
    model_config = ConfigDict(populate_by_name=True)

    status: int
    data: WeatherReadingResponse | None = None
    error: str | None = None
