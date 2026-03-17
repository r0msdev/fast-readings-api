from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    mock_db = MagicMock()
    mock_queue = MagicMock()
    with (
        patch("app.infrastructure.database.mongo.get_database", return_value=mock_db),
        patch("app.infrastructure.messaging.queue.ping", return_value=None),
        patch.dict(
            "sys.modules",
            {"app.infrastructure.messaging.queue": mock_queue},
        ),
    ):
        mock_queue.ping.return_value = None
        client = TestClient(app)
        response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
