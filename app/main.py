import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from app.config import settings
from app.exception_handlers import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.routers import health, weather

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logging.basicConfig(level=settings.log_level.upper())
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(ValidationError, validation_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(health.router)
app.include_router(weather.router)


