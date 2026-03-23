"""Health-check endpoints for liveness and readiness probes."""
import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def liveness() -> JSONResponse:
    """Liveness probe — confirms the process is running.

    Performs no I/O. Container orchestrators (Docker, Azure Container Apps)
    should use this endpoint to decide whether to restart the container.
    A broker or DB outage must never trigger a restart.
    """
    return JSONResponse(status_code=200, content={"status": "ok"})


@router.get("/health/ready")
@router.get("/health")
async def readiness() -> JSONResponse:
    """Readiness probe — checks database and message broker reachability.

    Returns HTTP 200 with status "degraded" when a dependency is unavailable
    so monitoring tools can read the body without triggering false alerts.
    Use this endpoint to decide whether to route traffic to the instance.
    """
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
