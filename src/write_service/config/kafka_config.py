from pydantic import Field

from write_service.config.base import BaseConfig


class KafkaConfig(BaseConfig):
    """Kafka producer settings for vector upsert events."""

    model_config = {"env_prefix": "KAFKA_"}

    bootstrap_servers: str = Field(default="localhost:9092")
    topic_upsert: str = Field(default="vector-upserted")
    client_id: str = Field(default="matching-write-service")
    security_protocol: str = Field(default="PLAINTEXT")
    sasl_mechanism: str | None = Field(default=None)
    sasl_username: str | None = Field(default=None)
    sasl_password: str | None = Field(default=None)
    acks: str = Field(default="all")
    linger_ms: int = Field(default=50, ge=0, le=5000)
    compression_type: str = Field(default="lz4")

