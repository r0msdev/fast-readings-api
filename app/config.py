"""Application configuration loaded from environment variables or a .env file."""
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings; values are read from env vars and the .env file."""
    app_name: str = "Weather API"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "info"

    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "readings"

    # Messaging
    messaging_backend: Literal["rabbitmq", "servicebus"] = "rabbitmq"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    messaging_queue_name: str = "stats-recalculate"
    azure_servicebus_namespace: str = ""
    azure_servicebus_connection_string: str = ""

    @model_validator(mode="after")
    def _validate_messaging_credentials(self) -> "Settings":
        if self.messaging_backend == "rabbitmq":
            if not self.rabbitmq_url:
                raise ValueError(
                    "messaging_backend='rabbitmq' requires RABBITMQ_URL"
                )
        elif self.messaging_backend == "servicebus":
            if not self.azure_servicebus_namespace and not self.azure_servicebus_connection_string:
                raise ValueError(
                    "messaging_backend='servicebus' requires either "
                    "AZURE_SERVICEBUS_NAMESPACE or AZURE_SERVICEBUS_CONNECTION_STRING"
                )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
