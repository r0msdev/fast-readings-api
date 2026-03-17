"""Application configuration loaded from environment variables or a .env file."""
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
    messaging_backend: str = "rabbitmq"  # "rabbitmq" | "servicebus"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    service_bus_queue_name: str = ""
    azure_servicebus_namespace: str = ""
    azure_servicebus_connection_string: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
