"""Tests for weather sensor stats endpoints."""
import unittest
from contextlib import ExitStack
from datetime import datetime, timezone
from unittest.mock import patch

import mongomock
import app.infrastructure.database.mongo as _storage
from fastapi.testclient import TestClient

from app.domain.repositories.collections import STATS_COLLECTION
from app.main import app

SENSOR_NAME = 'aemet-zaorejas'
STAT_DATE = '2026-02-15'
STAT_DATETIME = datetime(2026, 2, 15, tzinfo=timezone.utc)

STATS_DOC = {
    'sensorName': SENSOR_NAME,
    'date': STAT_DATETIME,
    'readingCount': 2,
    'stats': {
        'Temperature': {'avg': 5.0, 'min': 4.0, 'max': 6.0},
        'Humidity': {'avg': 85.0, 'min': 80.0, 'max': 90.0},
    },
}


class DailySensorStatsTests(unittest.TestCase):

    def setUp(self):
        self.mock_db = mongomock.MongoClient()['readings']
        _storage.reset_client()
        self._stack = ExitStack()
        self._stack.enter_context(
            patch('app.infrastructure.database.mongo.get_database', return_value=self.mock_db)
        )
        self.client = self._stack.enter_context(TestClient(app))
        self.url = f'/weather/{SENSOR_NAME}/stats/'

    def tearDown(self):
        self._stack.close()
        _storage.reset_client()

    def _insert_stats(self, **overrides):
        doc = {**STATS_DOC, **overrides}
        self.mock_db[STATS_COLLECTION].insert_one(doc)

    # --- list (no date filter) ---

    def test_list_returns_empty_when_no_stats(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['results'], [])

    def test_list_returns_all_stats_for_sensor(self):
        self._insert_stats()
        self._insert_stats(date=datetime(2026, 2, 16, tzinfo=timezone.utc))
        data = self.client.get(self.url).json()
        self.assertEqual(data['count'], 2)

    def test_list_excludes_other_sensors(self):
        self._insert_stats()
        self._insert_stats(sensorName='other-sensor')
        data = self.client.get(self.url).json()
        self.assertEqual(data['count'], 1)

    # --- filtered by ?sensorDate ---

    def test_filtered_returns_404_when_no_stats(self):
        response = self.client.get(self.url, params={'sensorDate': STAT_DATE})
        self.assertEqual(response.status_code, 404)

    def test_filtered_returns_404_for_unknown_sensor(self):
        self._insert_stats()
        response = self.client.get(
            f'/weather/unknown-sensor/stats/', params={'sensorDate': STAT_DATE}
        )
        self.assertEqual(response.status_code, 404)

    def test_filtered_returns_200_with_stats(self):
        self._insert_stats()
        response = self.client.get(self.url, params={'sensorDate': STAT_DATE})
        self.assertEqual(response.status_code, 200)

    def test_filtered_response_shape(self):
        self._insert_stats()
        data = self.client.get(self.url, params={'sensorDate': STAT_DATE}).json()
        self.assertEqual(data['count'], 1)
        item = data['results'][0]
        self.assertEqual(item['sensorName'], SENSOR_NAME)
        self.assertEqual(item['date'], STAT_DATE)
        self.assertEqual(item['readingCount'], 2)
        temp = item['stats']['Temperature']
        self.assertEqual(temp['avg'], 5.0)
        self.assertEqual(temp['min'], 4.0)
        self.assertEqual(temp['max'], 6.0)

    def test_filtered_does_not_return_stats_for_different_date(self):
        self._insert_stats(date=datetime(2026, 2, 16, tzinfo=timezone.utc))
        response = self.client.get(self.url, params={'sensorDate': STAT_DATE})
        self.assertEqual(response.status_code, 404)
