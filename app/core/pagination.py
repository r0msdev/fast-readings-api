"""Pagination helpers for FastAPI query parameters and paginated response models."""
import math
from typing import Generic, TypeVar

from fastapi import Query, Request
from pydantic import BaseModel

T = TypeVar('T')


class PaginationParams:  # pylint: disable=too-few-public-methods
    """Dependency-injectable pagination parameters parsed from query string."""
    def __init__(
        self,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, alias='pageSize', ge=1, le=100),
    ):
        self.page = page
        self.page_size = page_size
        self.skip = (page - 1) * page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic envelope returned by paginated list endpoints."""
    count: int
    next: str | None
    previous: str | None
    results: list[T]


def paginate(
    request: Request,
    all_results: list[T],
    pagination: PaginationParams,
) -> PaginatedResponse[T]:
    """Slice results and build next/previous URLs from the current request URL."""
    total = len(all_results)
    page_results = all_results[pagination.skip: pagination.skip + pagination.page_size]
    total_pages = math.ceil(total / pagination.page_size) if pagination.page_size else 1

    def page_url(page: int) -> str:
        params = dict(request.query_params)
        params['page'] = str(page)
        query = '&'.join(f'{k}={v}' for k, v in params.items())
        return str(request.url.replace(query=query))

    next_url = page_url(pagination.page + 1) if pagination.page < total_pages else None
    prev_url = page_url(pagination.page - 1) if pagination.page > 1 else None

    return PaginatedResponse(
        count=total,
        next=next_url,
        previous=prev_url,
        results=page_results,
    )
