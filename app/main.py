"""FastAPI application factory — wires handlers, middleware, and exception handlers."""
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from app.config import settings
from app.core.exceptions import DuplicateResourceError
from app.core.middleware import CorrelationIdMiddleware
from app.exception_handlers import (
    conflict_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.routers import health, readings as readings_router

logger = logging.getLogger(__name__)


def _register_handlers() -> None:  # pylint: disable=too-many-locals
    from app.core.bus import command_bus, query_bus  # pylint: disable=import-outside-toplevel
    from app.commands.create_reading import (  # pylint: disable=import-outside-toplevel
        CreateReadingCommand, CreateReadingHandler,
    )
    from app.commands.delete_reading import (  # pylint: disable=import-outside-toplevel
        DeleteReadingCommand, DeleteReadingHandler,
    )
    from app.queries.readings import (  # pylint: disable=import-outside-toplevel
        GetReadingByIdQuery, GetReadingByIdHandler,
        ListReadingsQuery, ListReadingsHandler,
    )
    from app.queries.stats import (  # pylint: disable=import-outside-toplevel
        GetDailyStatsQuery, GetDailyStatsHandler,
        GetStatsListQuery, GetStatsListHandler,
    )

    create_handler = CreateReadingHandler()
    delete_handler = DeleteReadingHandler()
    list_handler = ListReadingsHandler()
    get_by_id_handler = GetReadingByIdHandler()
    stats_list_handler = GetStatsListHandler()
    daily_stats_handler = GetDailyStatsHandler()

    command_bus.register(CreateReadingCommand, create_handler.handle)
    command_bus.register(DeleteReadingCommand, delete_handler.handle)
    query_bus.register(ListReadingsQuery, list_handler.handle)
    query_bus.register(GetReadingByIdQuery, get_by_id_handler.handle)
    query_bus.register(GetStatsListQuery, stats_list_handler.handle)
    query_bus.register(GetDailyStatsQuery, daily_stats_handler.handle)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Configure logging, register bus handlers, and ensure MongoDB indexes."""
    logging.basicConfig(level=settings.log_level.upper())
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)

    # Import here to trigger @register_indexes decorators in repository modules
    import app.domain.repositories.readings  # noqa: F401  pylint: disable=import-outside-toplevel,redefined-outer-name,unused-import
    import app.domain.repositories.stats     # noqa: F401  pylint: disable=import-outside-toplevel,redefined-outer-name,unused-import

    _register_handlers()

    from app.infrastructure.database.mongo import ensure_indexes  # pylint: disable=import-outside-toplevel
    ensure_indexes()

    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(CorrelationIdMiddleware)

app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(  # type: ignore[arg-type]
    DuplicateResourceError, conflict_exception_handler
)
app.add_exception_handler(ValidationError, validation_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(health.router)
app.include_router(readings_router.router)
