from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

_DB_PATH = "app.infrastructure.database.mongo.get_database"
_QUEUE_PING_PATH = "app.infrastructure.messaging.queue.ping"


def test_liveness() -> None:
    client = TestClient(app)
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness() -> None:
    mock_db = MagicMock()
    with patch(_DB_PATH, return_value=mock_db), patch(_QUEUE_PING_PATH):
        client = TestClient(app)
        response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "db" in body
    assert "messaging" in body


def test_health_backward_compat() -> None:
    """GET /health must continue to work — it is aliased to /health/ready."""
    mock_db = MagicMock()
    with patch(_DB_PATH, return_value=mock_db), patch(_QUEUE_PING_PATH):
        client = TestClient(app)
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness_degraded_when_db_fails() -> None:
    with (
        patch(_DB_PATH, side_effect=Exception("mongo down")),
        patch(_QUEUE_PING_PATH),
    ):
        client = TestClient(app)
        response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["db"] == "error"
    assert body["messaging"] == "ok"
