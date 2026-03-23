"""API router for the weather readings and sensor stats endpoints."""
import logging
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status

from app.api import mapper
from app.api.read_models import BatchResultItem, DailySensorStatsResponse, WeatherReadingResponse
from app.api.write_models import CreateReadingRequest, CreateReadingsBatchRequest
from app.commands.create_reading import CreateReadingCommand
from app.commands.create_readings_batch import CreateReadingsBatchCommand
from app.commands.delete_reading import DeleteReadingCommand
from app.core.bus import command_bus, query_bus
from app.core.pagination import Page, PaginatedResponse, PaginationParams, build_paginated_response
from app.queries.readings import GetReadingByIdQuery, ListReadingsQuery
from app.queries.stats import GetDailyStatsQuery, GetStatsListQuery

logger = logging.getLogger('weather')

router = APIRouter(prefix='/weather', tags=['weather'])

_SENSOR_NAME_PATH = Annotated[str, Path(min_length=1, max_length=100, pattern=r'^[\w\-]+$')]  # pylint: disable=invalid-name
_READING_ID_PATH = Annotated[str, Path(min_length=24, max_length=24, pattern=r'^[0-9a-f]{24}$')]  # pylint: disable=invalid-name


@router.get('/')
def list_all_readings(
    request: Request,
    pagination: Annotated[PaginationParams, Depends(PaginationParams)],
    sensor_date: Annotated[date | None, Query(alias='sensorDate')] = None,
) -> PaginatedResponse[WeatherReadingResponse]:
    """GET /weather/ — return all readings across all sensors, with optional date filtering.
    """
    page = query_bus.dispatch(ListReadingsQuery(
        sensor_name=None,
        sensor_date=sensor_date,
        skip=pagination.skip,
        limit=pagination.page_size,
    ))
    mapped = Page(items=[mapper.reading_to_dto(e) for e in page.items], total=page.total)
    return build_paginated_response(request, mapped, pagination)


@router.get('/{sensor_name}/')
def list_readings_by_sensor(
    request: Request,
    sensor_name: _SENSOR_NAME_PATH,
    pagination: Annotated[PaginationParams, Depends(PaginationParams)],
    sensor_date: Annotated[date | None, Query(alias='sensorDate')] = None,
) -> PaginatedResponse[WeatherReadingResponse]:
    """GET /weather/{sensor_name}/ — return readings for one sensor, with optional date filtering.
    """
    page = query_bus.dispatch(ListReadingsQuery(
        sensor_name=sensor_name,
        sensor_date=sensor_date,
        skip=pagination.skip,
        limit=pagination.page_size,
    ))
    mapped = Page(items=[mapper.reading_to_dto(e) for e in page.items], total=page.total)
    return build_paginated_response(request, mapped, pagination)


@router.post('/{sensor_name}/', status_code=status.HTTP_201_CREATED)
def create_reading(
    sensor_name: _SENSOR_NAME_PATH, body: CreateReadingRequest,
) -> WeatherReadingResponse:
    """POST /weather/{sensor_name}/ — create a new reading for the given sensor,
    rejecting duplicates.
    """
    if body.sensor_name != sensor_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={'sensorName': 'Must match the sensor name in the URL.'},
        )
    cmd = CreateReadingCommand(
        sensor_name=sensor_name,
        sensor_date=body.sensor_date,
        data_info=body.data_info,
    )
    entity = command_bus.dispatch(cmd)
    return mapper.reading_to_dto(entity)


_STATS_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {'description': 'No stats found for the given sensor or date.'},
}


@router.get('/{sensor_name}/stats/', responses=_STATS_RESPONSES)
def get_stats(
    request: Request,
    sensor_name: _SENSOR_NAME_PATH,
    pagination: Annotated[PaginationParams, Depends(PaginationParams)],
    sensor_date: Annotated[date | None, Query(alias='sensorDate')] = None,
) -> PaginatedResponse[DailySensorStatsResponse]:
    """GET /weather/{sensor_name}/stats/ — return pre-aggregated stats,
    optionally filtered to a single date.

    Defined before /{reading_id}/ to prevent FastAPI matching the literal 'stats' as an ObjectId.
    """
    if sensor_date is not None:
        result = query_bus.dispatch(
            GetDailyStatsQuery(sensor_name=sensor_name, date=sensor_date)
        )
        return PaginatedResponse(
            count=1, next=None, previous=None, results=[mapper.stats_to_dto(result)]
        )
    page = query_bus.dispatch(GetStatsListQuery(
        sensor_name=sensor_name,
        skip=pagination.skip,
        limit=pagination.page_size,
    ))
    mapped = Page(items=[mapper.stats_to_dto(e) for e in page.items], total=page.total)
    return build_paginated_response(request, mapped, pagination)


@router.post('/{sensor_name}/batch/', status_code=status.HTTP_207_MULTI_STATUS)
def create_readings_batch(
    sensor_name: _SENSOR_NAME_PATH,
    body: CreateReadingsBatchRequest,
) -> list[BatchResultItem]:
    """POST /weather/{sensor_name}/batch/ — create multiple readings, returning per-item outcomes.

    Defined before /{reading_id}/ to prevent FastAPI matching 'batch' as an ObjectId.
    """
    for item in body.items:
        if item.sensor_name != sensor_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={'sensorName': 'All items must match the sensor name in the URL.'},
            )
    cmd = CreateReadingsBatchCommand(
        sensor_name=sensor_name,
        items=[(item.sensor_date, item.data_info) for item in body.items],
    )
    return command_bus.dispatch(cmd)


_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {'description': 'Reading not found.'}
}


@router.get('/{sensor_name}/{reading_id}/', responses=_NOT_FOUND)
def get_reading(
    sensor_name: _SENSOR_NAME_PATH, reading_id: _READING_ID_PATH,
) -> WeatherReadingResponse:
    """GET /weather/{sensor_name}/{reading_id}/ — return a single reading
    by sensor name and ObjectId.
    """
    reading = query_bus.dispatch(
        GetReadingByIdQuery(sensor_name=sensor_name, reading_id=reading_id)
    )
    return mapper.reading_to_dto(reading)


@router.delete(
    '/{sensor_name}/{reading_id}/',
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_NOT_FOUND,
)
def delete_reading(sensor_name: _SENSOR_NAME_PATH, reading_id: _READING_ID_PATH) -> None:
    """DELETE /weather/{sensor_name}/{reading_id}/ — delete a reading by sensor name and ObjectId,
    returning 404 if absent.
    """
    command_bus.dispatch(
        DeleteReadingCommand(sensor_name=sensor_name, reading_id=reading_id)
    )
