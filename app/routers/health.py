"""Health-check endpoint reporting the status of the database and message broker."""
import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> JSONResponse:
    """Return liveness and component status for the running service."""
    db_status = "ok"
    messaging_status = "ok"

    try:
        from app.infrastructure.database.mongo import get_database  # pylint: disable=import-outside-toplevel
        get_database().command("ping")
    except Exception:  # pylint: disable=broad-except
        logger.exception("Health check: MongoDB ping failed")
        db_status = "error"

    try:
        from app.infrastructure.messaging import queue  # pylint: disable=import-outside-toplevel
        queue.ping()
    except Exception:  # pylint: disable=broad-except
        logger.exception("Health check: messaging ping failed")
        messaging_status = "error"

    overall = "ok" if db_status == "ok" and messaging_status == "ok" else "degraded"
    return JSONResponse(
        status_code=200,
        content={
            "status": overall,
            "version": settings.app_version,
            "db": db_status,
            "messaging": messaging_status,
        },
    )
