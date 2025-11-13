from pydantic import Field

from search_service.config.base import BaseConfig


class KafkaConfig(BaseConfig):
    """Kafka consumer configuration for warming caches or reacting to events."""

    model_config = {"env_prefix": "KAFKA_"}

    bootstrap_servers: str = Field(default="localhost:9092")
    topic_upsert: str = Field(default="vector-upserted")
    group_id: str = Field(default="matching-search-service")
    client_id: str = Field(default="matching-search-service")
    security_protocol: str = Field(default="PLAINTEXT")
    sasl_mechanism: str | None = Field(default=None)
    sasl_username: str | None = Field(default=None)
    sasl_password: str | None = Field(default=None)
    auto_offset_reset: str = Field(default="latest")
