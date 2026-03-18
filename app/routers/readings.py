"""API router for the weather readings and sensor stats endpoints."""
import logging
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api import mapper
from app.api.read_models import DailySensorStatsResponse, WeatherReadingResponse
from app.api.write_models import CreateReadingRequest
from app.commands.create_reading import CreateReadingCommand
from app.commands.delete_reading import DeleteReadingCommand
from app.core.bus import command_bus, query_bus
from app.core.exceptions import DuplicateResourceError
from app.core.pagination import Page, PaginatedResponse, PaginationParams, build_paginated_response
from app.queries.readings import GetReadingByIdQuery, ListReadingsQuery
from app.queries.stats import GetDailyStatsQuery, GetStatsListQuery

logger = logging.getLogger('weather')

router = APIRouter(prefix='/weather', tags=['weather'])


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
    sensor_name: str,
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
def create_reading(sensor_name: str, body: CreateReadingRequest) -> WeatherReadingResponse:
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
    try:
        entity = command_bus.dispatch(cmd)
        return mapper.reading_to_dto(entity)
    except DuplicateResourceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


_STATS_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {'description': 'No stats found for the given sensor or date.'},
}


@router.get('/{sensor_name}/stats/', responses=_STATS_RESPONSES)
def get_stats(
    request: Request,
    sensor_name: str,
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


_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {'description': 'Reading not found.'}
}


@router.get('/{sensor_name}/{reading_id}/', responses=_NOT_FOUND)
def get_reading(sensor_name: str, reading_id: str) -> WeatherReadingResponse:
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
def delete_reading(sensor_name: str, reading_id: str) -> None:
    """DELETE /weather/{sensor_name}/{reading_id}/ — delete a reading by sensor name and ObjectId,
    returning 404 if absent.
    """
    command_bus.dispatch(
        DeleteReadingCommand(sensor_name=sensor_name, reading_id=reading_id)
    )
