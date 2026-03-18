"""Tests for weather readings endpoints."""
import unittest
from contextlib import ExitStack
from datetime import datetime, timezone
from typing import Any
from unittest.mock import patch

import mongomock
import app.infrastructure.database.mongo as _storage
from bson import ObjectId
from fastapi.testclient import TestClient

from app.domain.entities import WeatherReading
from app.domain.repositories import readings as repo
from app.main import app

DATA_INFO = {
    'Temperature': 3.8,
    'TemperatureMax': 3.8,
    'TemperatureMin': 3.4,
    'Humidity': 89,
    'Rainfall': 0,
}


def _make_reading(
    sensor_name: str = 'aemet-zaorejas',
    sensor_date: datetime = datetime(2026, 2, 15, 23, 0, 0, tzinfo=timezone.utc),
    data_info: dict[str, float] = DATA_INFO,
) -> WeatherReading:
    return repo.create_reading(WeatherReading(
        sensor_name=sensor_name,
        sensor_date=sensor_date,
        data_info=data_info,
    ))


def _db_patch(mock_db):
    return patch('app.infrastructure.database.mongo.get_database', return_value=mock_db)


class WeatherReadingListGetTests(unittest.TestCase):

    def setUp(self):
        self.mock_db = mongomock.MongoClient()['readings']
        _storage.reset_client()
        self._stack = ExitStack()
        self._stack.enter_context(_db_patch(self.mock_db))
        self.client = self._stack.enter_context(TestClient(app))

    def tearDown(self):
        self._stack.close()
        _storage.reset_client()

    def _get_data(self, params: dict[str, str | int] | None = None) -> Any:
        return self.client.get('/weather/', params=params or {}).json()

    def test_empty_list(self):
        response = self.client.get('/weather/')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['results'], [])
        self.assertEqual(body['count'], 0)

    def test_returns_all_readings(self):
        _make_reading()
        _make_reading(sensor_date=datetime(2026, 2, 15, 22, 0, 0, tzinfo=timezone.utc))
        body = self._get_data()
        self.assertEqual(body['count'], 2)
        self.assertEqual(len(body['results']), 2)

    def test_post_not_allowed(self):
        response = self.client.post('/weather/', json={})
        self.assertEqual(response.status_code, 405)

    def test_response_shape(self):
        reading = _make_reading()
        body = self._get_data()
        self.assertIn('count', body)
        self.assertIn('next', body)
        self.assertIn('previous', body)
        self.assertIn('results', body)
        item = body['results'][0]
        self.assertEqual(item['id'], reading.id)
        self.assertEqual(item['sensorName'], reading.sensor_name)
        self.assertIn('sensorDate', item)
        self.assertEqual(item['dataInfo'], DATA_INFO)

    def test_pagination_page_size(self):
        for i in range(5):
            _make_reading(sensor_date=datetime(2026, 2, 10 + i, 0, 0, 0, tzinfo=timezone.utc))
        body = self._get_data({'pageSize': 2})
        self.assertEqual(body['count'], 5)
        self.assertEqual(len(body['results']), 2)
        self.assertIsNotNone(body['next'])

    def test_pagination_second_page(self):
        for i in range(4):
            _make_reading(sensor_date=datetime(2026, 2, 10 + i, 0, 0, 0, tzinfo=timezone.utc))
        body = self._get_data({'pageSize': 2, 'page': 2})
        self.assertEqual(len(body['results']), 2)
        self.assertIsNotNone(body['previous'])
        self.assertIsNone(body['next'])

    def test_invalid_page_returns_422(self):
        # FastAPI validates page as int — non-integer value is rejected at the parameter level
        response = self.client.get('/weather/', params={'page': 'abc'})
        self.assertEqual(response.status_code, 422)

    def test_invalid_page_size_returns_422(self):
        # FastAPI validates pageSize as int — non-integer value is rejected at the parameter level
        _make_reading()
        response = self.client.get('/weather/', params={'pageSize': 'abc'})
        self.assertEqual(response.status_code, 422)

    def test_filter_by_sensor_date_match(self):
        _make_reading(sensor_date=datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc))
        _make_reading(sensor_date=datetime(2026, 2, 16, 10, 0, 0, tzinfo=timezone.utc))
        body = self._get_data({'sensorDate': '2026-02-15'})
        self.assertEqual(body['count'], 1)
        self.assertIn('2026-02-15', body['results'][0]['sensorDate'])

    def test_filter_by_sensor_date_no_match(self):
        _make_reading(sensor_date=datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc))
        body = self._get_data({'sensorDate': '2026-03-01'})
        self.assertEqual(body['count'], 0)

    def test_filter_by_sensor_date_invalid_format(self):
        response = self.client.get('/weather/', params={'sensorDate': 'not-a-date'})
        self.assertEqual(response.status_code, 422)


class WeatherReadingListPostTests(unittest.TestCase):

    def setUp(self):
        self.mock_db = mongomock.MongoClient()['readings']
        _storage.reset_client()
        self._stack = ExitStack()
        self._stack.enter_context(_db_patch(self.mock_db))
        self.mock_publish = self._stack.enter_context(
            patch('app.messaging.handlers.publish_reading_changed')
        )
        self.client = self._stack.enter_context(TestClient(app))
        self.url = '/weather/aemet-zaorejas/'
        self.payload = {
            'sensorName': 'aemet-zaorejas',
            'sensorDate': '2026-02-15T23:00:00+00:00',
            'dataInfo': DATA_INFO,
        }

    def tearDown(self):
        self._stack.close()
        _storage.reset_client()

    def _post(self, payload):
        return self.client.post(self.url, json=payload)

    def test_create_reading_returns_201(self):
        response = self._post(self.payload)
        self.assertEqual(response.status_code, 201)

    def test_create_reading_publishes_event(self):
        self._post(self.payload)
        self.mock_publish.assert_called_once()

    def test_create_reading_persisted(self):
        self._post(self.payload)
        body = self.client.get(self.url).json()
        self.assertEqual(body['count'], 1)

    def test_create_reading_response_shape(self):
        data = self._post(self.payload).json()
        self.assertIn('id', data)
        self.assertEqual(len(data['id']), 24)  # MongoDB ObjectId hex string
        self.assertEqual(data['sensorName'], 'aemet-zaorejas')
        self.assertEqual(data['dataInfo'], DATA_INFO)

    def test_missing_sensor_name_returns_422(self):
        payload = {k: v for k, v in self.payload.items() if k != 'sensorName'}
        response = self._post(payload)
        self.assertEqual(response.status_code, 422)
        self.assertIn('sensorName', response.text)

    def test_missing_sensor_date_returns_422(self):
        payload = {k: v for k, v in self.payload.items() if k != 'sensorDate'}
        response = self._post(payload)
        self.assertEqual(response.status_code, 422)

    def test_missing_data_info_returns_422(self):
        payload = {k: v for k, v in self.payload.items() if k != 'dataInfo'}
        response = self._post(payload)
        self.assertEqual(response.status_code, 422)

    def test_data_info_not_object_returns_422(self):
        response = self._post({**self.payload, 'dataInfo': 'not-an-object'})
        self.assertEqual(response.status_code, 422)

    def test_sensor_name_array_returns_422(self):
        response = self._post({**self.payload, 'sensorName': []})
        self.assertEqual(response.status_code, 422)
        self.assertIn('sensorName', response.text)

    def test_empty_sensor_name_returns_422(self):
        # Empty sensorName fails the URL-mismatch guard in the route handler
        response = self._post({**self.payload, 'sensorName': ''})
        self.assertEqual(response.status_code, 422)
        self.assertIn('sensorName', response.text)

    def test_invalid_json_returns_422(self):
        response = self.client.post(
            self.url,
            content=b'not json',
            headers={'content-type': 'application/json'},
        )
        self.assertEqual(response.status_code, 422)

    def test_sensor_name_mismatch_returns_422(self):
        response = self._post({**self.payload, 'sensorName': 'different-sensor'})
        self.assertEqual(response.status_code, 422)
        self.assertIn('sensorName', response.text)

    def test_duplicate_reading_returns_409(self):
        self._post(self.payload)
        response = self._post(self.payload)
        self.assertEqual(response.status_code, 409)

    def test_same_sensor_different_date_returns_201(self):
        self._post(self.payload)
        response = self._post({**self.payload, 'sensorDate': '2026-02-16T23:00:00+00:00'})
        self.assertEqual(response.status_code, 201)


class WeatherReadingDetailGetTests(unittest.TestCase):

    def setUp(self):
        self.mock_db = mongomock.MongoClient()['readings']
        _storage.reset_client()
        self._stack = ExitStack()
        self._stack.enter_context(_db_patch(self.mock_db))
        self.client = self._stack.enter_context(TestClient(app))
        self.reading = _make_reading()
        self.url = f'/weather/{self.reading.sensor_name}/{self.reading.id}/'

    def tearDown(self):
        self._stack.close()
        _storage.reset_client()

    def test_returns_200_for_existing(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_response_shape(self):
        data = self.client.get(self.url).json()
        self.assertEqual(data['id'], self.reading.id)
        self.assertEqual(data['sensorName'], self.reading.sensor_name)
        self.assertEqual(data['dataInfo'], DATA_INFO)

    def test_returns_404_for_unknown_id(self):
        url = f'/weather/{self.reading.sensor_name}/{ObjectId()}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class WeatherReadingDeleteTests(unittest.TestCase):

    def setUp(self):
        self.mock_db = mongomock.MongoClient()['readings']
        _storage.reset_client()
        self._stack = ExitStack()
        self._stack.enter_context(_db_patch(self.mock_db))
        self.mock_publish = self._stack.enter_context(
            patch('app.messaging.handlers.publish_reading_changed')
        )
        self.client = self._stack.enter_context(TestClient(app))
        self.reading = _make_reading()
        self.url = f'/weather/{self.reading.sensor_name}/{self.reading.id}/'

    def tearDown(self):
        self._stack.close()
        _storage.reset_client()

    def test_returns_204_for_existing(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 204)

    def test_delete_publishes_event(self):
        self.client.delete(self.url)
        self.mock_publish.assert_called_once()

    def test_returns_404_for_unknown_id(self):
        url = f'/weather/{self.reading.sensor_name}/{ObjectId()}/'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 404)

    def test_not_found_does_not_publish_event(self):
        url = f'/weather/{self.reading.sensor_name}/{ObjectId()}/'
        self.client.delete(url)
        self.mock_publish.assert_not_called()

    def test_reading_removed_after_delete(self):
        self.client.delete(self.url)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_delete_scoped_to_sensor(self):
        url = f'/weather/other-sensor/{self.reading.id}/'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 404)
        # original reading must still exist under its own sensor
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
