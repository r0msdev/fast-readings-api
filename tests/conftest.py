"""Shared pytest fixtures — applied automatically to all tests."""
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _mock_broker_ping():
    """Prevent real broker connections during every test.

    The lifespan now calls queue.ping() at startup.  Individual tests that
    want to assert on broker reachability (e.g. test_health.py) may override
    this by applying their own patch inside the test body.
    """
    with patch('app.infrastructure.messaging.queue.ping'):
        yield
