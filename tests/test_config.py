"""Tests for Settings config validation."""
import pytest
from pydantic import ValidationError

from app.config import Settings


def test_rabbitmq_backend_is_valid() -> None:
    s = Settings(messaging_backend='rabbitmq')
    assert s.messaging_backend == 'rabbitmq'


def test_rabbitmq_with_empty_url_raises() -> None:
    with pytest.raises(ValidationError, match='RABBITMQ_URL'):
        Settings(messaging_backend='rabbitmq', rabbitmq_url='')


def test_servicebus_missing_both_credentials_raises() -> None:
    with pytest.raises(ValidationError, match='AZURE_SERVICEBUS'):
        Settings(
            messaging_backend='servicebus',
            azure_servicebus_namespace='',
            azure_servicebus_connection_string='',
        )


def test_invalid_messaging_backend_raises() -> None:
    with pytest.raises(ValidationError):
        Settings(messaging_backend='kafka')  # type: ignore[arg-type]


def test_servicebus_without_credentials_raises() -> None:
    with pytest.raises(ValidationError, match='AZURE_SERVICEBUS'):
        Settings(messaging_backend='servicebus')


def test_servicebus_with_namespace_is_valid() -> None:
    s = Settings(
        messaging_backend='servicebus',
        azure_servicebus_namespace='foo.servicebus.windows.net',
    )
    assert s.messaging_backend == 'servicebus'


def test_servicebus_with_connection_string_is_valid() -> None:
    s = Settings(
        messaging_backend='servicebus',
        azure_servicebus_connection_string='Endpoint=sb://foo.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=abc123',
    )
    assert s.messaging_backend == 'servicebus'


def test_servicebus_with_both_credentials_is_valid() -> None:
    """Namespace takes precedence, but having both is still accepted."""
    s = Settings(
        messaging_backend='servicebus',
        azure_servicebus_namespace='foo.servicebus.windows.net',
        azure_servicebus_connection_string='Endpoint=sb://foo.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=abc123',
    )
    assert s.messaging_backend == 'servicebus'
