"""API router for the weather readings and sensor stats endpoints."""
import logging
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.read_models import DailySensorStatsDTO, WeatherReadingDTO
from app.commands.create_reading import CreateReadingCommand
from app.commands.delete_reading import DeleteReadingCommand
from app.core.bus import command_bus, query_bus
from app.core.exceptions import DuplicateResourceError
from app.core.pagination import PaginatedResponse, PaginationParams
from app.queries.readings import GetReadingByIdQuery, ListReadingsQuery
from app.queries.stats import GetDailyStatsQuery, GetStatsListQuery

logger = logging.getLogger('weather')

router = APIRouter(prefix='/weather', tags=['weather'])


class CreateReadingRequest(BaseModel):
    """Request body schema for creating a new reading under a sensor."""
    model_config = ConfigDict(populate_by_name=True)

    sensor_name: str = Field(alias='sensorName')
    sensor_date: datetime = Field(alias='sensorDate')
    data_info: dict[str, float] = Field(alias='dataInfo')


@router.get('/')
def list_all_readings(
    pagination: Annotated[PaginationParams, Depends(PaginationParams)],
    sensor_date: Annotated[date | None, Query(alias='sensorDate')] = None,
) -> PaginatedResponse[WeatherReadingDTO]:
    """GET /weather/ — return all readings across all sensors, with optional date filtering.
    """
    results = query_bus.dispatch(ListReadingsQuery(sensor_name=None, sensor_date=sensor_date))
    page_results = results[pagination.skip: pagination.skip + pagination.page_size]
    return PaginatedResponse(count=len(results), next=None, previous=None, results=page_results)


@router.get('/{sensor_name}/')
def list_readings_by_sensor(
    sensor_name: str,
    pagination: Annotated[PaginationParams, Depends(PaginationParams)],
    sensor_date: Annotated[date | None, Query(alias='sensorDate')] = None,
) -> PaginatedResponse[WeatherReadingDTO]:
    """GET /weather/{sensor_name}/ — return readings for one sensor, with optional date filtering.
    """
    results = query_bus.dispatch(
        ListReadingsQuery(sensor_name=sensor_name, sensor_date=sensor_date)
    )
    page_results = results[pagination.skip: pagination.skip + pagination.page_size]
    return PaginatedResponse(count=len(results), next=None, previous=None, results=page_results)


@router.post('/{sensor_name}/', status_code=status.HTTP_201_CREATED)
def create_reading(sensor_name: str, body: CreateReadingRequest) -> WeatherReadingDTO:
    """POST /weather/{sensor_name}/ — create a new reading for the given sensor,
    rejecting duplicates.
    """
    if body.sensor_name != sensor_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={'sensorName': 'Must match the sensor name in the URL.'},
        )
    cmd = CreateReadingCommand(
        sensor_name=sensor_name,
        sensor_date=body.sensor_date,
        data_info=body.data_info,
    )
    try:
        return command_bus.dispatch(cmd)
    except DuplicateResourceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get('/{sensor_name}/stats/')
def get_stats(
    sensor_name: str,
    sensor_date: Annotated[date | None, Query(alias='sensorDate')] = None,
) -> PaginatedResponse[DailySensorStatsDTO]:
    """GET /weather/{sensor_name}/stats/ — return pre-aggregated stats,
    optionally filtered to a single date.

    Defined before /{reading_id}/ to prevent FastAPI matching the literal 'stats' as an ObjectId.
    """
    if sensor_date is not None:
        result = query_bus.dispatch(
            GetDailyStatsQuery(sensor_name=sensor_name, date=sensor_date)
        )
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Stats not found.')
        return PaginatedResponse(count=1, next=None, previous=None, results=[result])
    results = query_bus.dispatch(GetStatsListQuery(sensor_name=sensor_name))
    return PaginatedResponse(count=len(results), next=None, previous=None, results=results)


@router.get('/{sensor_name}/{reading_id}/')
def get_reading(sensor_name: str, reading_id: str) -> WeatherReadingDTO:
    """GET /weather/{sensor_name}/{reading_id}/ — return a single reading
    by sensor name and ObjectId.
    """
    reading = query_bus.dispatch(
        GetReadingByIdQuery(sensor_name=sensor_name, reading_id=reading_id)
    )
    if reading is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Reading not found.')
    return reading


@router.delete('/{sensor_name}/{reading_id}/', status_code=status.HTTP_204_NO_CONTENT)
def delete_reading(sensor_name: str, reading_id: str) -> None:
    """DELETE /weather/{sensor_name}/{reading_id}/ — delete a reading by sensor name and ObjectId,
    returning 404 if absent.
    """
    deleted = command_bus.dispatch(
        DeleteReadingCommand(sensor_name=sensor_name, reading_id=reading_id)
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Reading not found.')
