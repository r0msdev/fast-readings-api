"""Pagination helpers for FastAPI query parameters and paginated response models."""
from typing import Generic, TypeVar

from fastapi import Query
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
