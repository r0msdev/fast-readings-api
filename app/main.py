"""FastAPI application factory — wires handlers, middleware, and exception handlers."""
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.core.middleware import CorrelationIdMiddleware
from app.exception_handlers import register_exception_handlers
from app.routers import health, readings as readings_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Configure logging, register bus handlers, and ensure MongoDB indexes."""
    logging.basicConfig(level=settings.log_level.upper())
    # Silence verbose INFO probing logs from third-party libraries
    logging.getLogger('pika').setLevel(logging.WARNING)
    logging.getLogger('azure.identity').setLevel(logging.WARNING)
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)

    # Import here to trigger @register_indexes decorators in repository modules
    import app.domain.repositories.readings  # pylint: disable=import-outside-toplevel,redefined-outer-name,unused-import
    import app.domain.repositories.stats     # pylint: disable=import-outside-toplevel,redefined-outer-name,unused-import

    from app.bootstrap import bootstrap_api  # pylint: disable=import-outside-toplevel
    bootstrap_api()

    from app.infrastructure.database.mongo import ensure_indexes  # pylint: disable=import-outside-toplevel
    ensure_indexes()

    from app.infrastructure.messaging import queue  # pylint: disable=import-outside-toplevel
    queue.ping()

    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(CorrelationIdMiddleware)

Instrumentator().instrument(app).expose(app)

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(readings_router.router)
