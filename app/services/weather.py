from uuid import UUID, uuid4

from app.database import db
from app.models import SensorReading, SensorReadingCreate


def get_all() -> list[SensorReading]:
    return list(db.values())


def get_by_id(reading_id: UUID) -> SensorReading | None:
    return db.get(reading_id)


def create(payload: SensorReadingCreate) -> SensorReading:
    reading = SensorReading(
        id=uuid4(),
        sensorName=payload.sensor_name,
        sensorDate=payload.sensor_date,
        dataInfo=payload.data_info,
    )
    db[reading.id] = reading
    return reading


def delete(reading_id: UUID) -> bool:
    if reading_id not in db:
        return False
    del db[reading_id]
    return True
