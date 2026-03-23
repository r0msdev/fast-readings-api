"""Pydantic request models for the API layer."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateReadingRequest(BaseModel):
    """Request body schema for creating a new reading under a sensor."""
    model_config = ConfigDict(populate_by_name=True)

    sensor_name: str = Field(
        alias='sensorName', min_length=1, max_length=100, pattern=r'^[\w\-]+$',
    )
    sensor_date: datetime = Field(alias='sensorDate')
    data_info: dict[str, float] = Field(alias='dataInfo', min_length=1)
