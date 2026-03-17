from uuid import UUID

from app.models import SensorReading

db: dict[UUID, SensorReading] = {}
