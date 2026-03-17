import pytest
from fastapi.testclient import TestClient
from typing import cast

from app.main import app
from app.database import db

SAMPLE_PAYLOAD: dict[str, object] = {
    "sensorName": "aemet-zaorejas",
    "sensorDate": "2026-02-15T23:00:00+00:00",
    "dataInfo": {
        "Temperature": 3.8,
        "TemperatureMax": 3.8,
        "TemperatureMin": 3.4,
        "Humidity": 89,
        "Rainfall": 0,
    },
}


@pytest.fixture(autouse=True)
def clear_db():
    """Reset in-memory store before each test."""
    db.clear()
    yield
    db.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# --- GET /weather ---

def test_get_all_readings_empty(client: TestClient) -> None:
    response = client.get("/weather")
    assert response.status_code == 200
    assert response.json() == []


def test_get_all_readings_returns_created(client: TestClient) -> None:
    client.post("/weather", json=SAMPLE_PAYLOAD)
    response = client.get("/weather")
    assert response.status_code == 200
    assert len(response.json()) == 1


# --- GET /weather/{id} ---

def test_get_reading_not_found(client: TestClient) -> None:
    response = client.get("/weather/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_get_reading_by_id(client: TestClient) -> None:
    created = client.post("/weather", json=SAMPLE_PAYLOAD).json()
    response = client.get(f"/weather/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


# --- POST /weather ---

def test_create_reading_returns_201(client: TestClient) -> None:
    response = client.post("/weather", json=SAMPLE_PAYLOAD)
    assert response.status_code == 201


def test_create_reading_persists_data(client: TestClient) -> None:
    response = client.post("/weather", json=SAMPLE_PAYLOAD)
    body = response.json()
    assert body["sensorName"] == SAMPLE_PAYLOAD["sensorName"]
    data_info = cast(dict[str, object], SAMPLE_PAYLOAD["dataInfo"])
    assert body["dataInfo"]["Temperature"] == data_info["Temperature"]


# --- DELETE /weather/{id} ---

def test_delete_reading(client: TestClient) -> None:
    created = client.post("/weather", json=SAMPLE_PAYLOAD).json()
    response = client.delete(f"/weather/{created['id']}")
    assert response.status_code == 204


def test_delete_reading_not_found(client: TestClient) -> None:
    response = client.delete("/weather/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_delete_reading_removes_from_store(client: TestClient) -> None:
    created = client.post("/weather", json=SAMPLE_PAYLOAD).json()
    client.delete(f"/weather/{created['id']}")
    response = client.get(f"/weather/{created['id']}")
    assert response.status_code == 404
