from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from confluent_kafka import Producer

from write_service.config.kafka_config import KafkaConfig

logger = logging.getLogger(__name__)


@dataclass
class VectorUpsertEvent:
    id: int
    text: str
    vector_dim: int
    timestamp_ms: int

    def to_json(self) -> bytes:
        return json.dumps(
            {
                "id": self.id,
                "text": self.text,
                "vector_dim": self.vector_dim,
                "timestamp_ms": self.timestamp_ms,
            },
            ensure_ascii=False,
        ).encode("utf-8")


class VectorEventProducer:
    """Minimal Kafka producer for vector lifecycle events."""

    def __init__(self, config: KafkaConfig) -> None:
        producer_config = {
            "bootstrap.servers": config.bootstrap_servers,
            "client.id": config.client_id,
            "security.protocol": config.security_protocol,
            "compression.type": config.compression_type,
            "linger.ms": config.linger_ms,
            "acks": config.acks,
        }
        if config.sasl_mechanism and config.sasl_username and config.sasl_password:
            producer_config.update(
                {
                    "sasl.mechanism": config.sasl_mechanism,
                    "sasl.username": config.sasl_username,
                    "sasl.password": config.sasl_password,
                }
            )
        self._producer = Producer(producer_config)
        self._topic = config.topic_upsert

    def publish_upsert(self, event: VectorUpsertEvent) -> None:
        logger.debug("Publishing vector upsert event id=%s", event.id)
        self._producer.produce(
            topic=self._topic,
            key=str(event.id),
            value=event.to_json(),
            on_delivery=self._on_delivery,
        )
        # Best-effort flush; letting librdkafka batch if needed.
        self._producer.poll(0)

    def flush(self) -> None:
        self._producer.flush()

    @staticmethod
    def _on_delivery(err, msg) -> None:
        if err is not None:
            logger.error("Failed to deliver Kafka message: %s", err)
        else:
            logger.debug("Delivered Kafka message to %s [%s]", msg.topic(), msg.partition())

