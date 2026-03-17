from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.models import SensorReading, SensorReadingCreate
from app.services import weather as weather_service

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("", response_model=list[SensorReading])
async def get_all_readings() -> list[SensorReading]:
    return weather_service.get_all()


@router.get("/{reading_id}", response_model=SensorReading)
async def get_reading(reading_id: UUID) -> SensorReading:
    reading = weather_service.get_by_id(reading_id)
    if not reading:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reading not found")
    return reading


@router.post("", response_model=SensorReading, status_code=status.HTTP_201_CREATED)
async def create_reading(payload: SensorReadingCreate) -> SensorReading:
    return weather_service.create(payload)


@router.delete("/{reading_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reading(reading_id: UUID) -> None:
    if not weather_service.delete(reading_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reading not found")
