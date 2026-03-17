from uuid import UUID, uuid4
from datetime import datetime

from pydantic import BaseModel, Field


class DataInfo(BaseModel):
    temperature: float = Field(alias="Temperature")
    temperature_max: float = Field(alias="TemperatureMax")
    temperature_min: float = Field(alias="TemperatureMin")
    humidity: float = Field(alias="Humidity")
    rainfall: float = Field(alias="Rainfall")

    model_config = {"populate_by_name": True}


class SensorReading(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    sensor_name: str = Field(alias="sensorName")
    sensor_date: datetime = Field(alias="sensorDate")
    data_info: DataInfo = Field(alias="dataInfo")

    model_config = {"populate_by_name": True}


class SensorReadingCreate(BaseModel):
    sensor_name: str = Field(alias="sensorName")
    sensor_date: datetime = Field(alias="sensorDate")
    data_info: DataInfo = Field(alias="dataInfo")

    model_config = {"populate_by_name": True}
