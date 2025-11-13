from __future__ import annotations

import asyncio
import json
import logging
from contextlib import suppress

from aiokafka import AIOKafkaConsumer

from search_service.config.kafka_config import KafkaConfig

logger = logging.getLogger(__name__)


class VectorEventConsumer:
    """Minimal Kafka consumer that keeps the group alive and logs upsert events."""

    def __init__(self, config: KafkaConfig) -> None:
        self._config = config
        self._consumer = AIOKafkaConsumer(
            config.topic_upsert,
            bootstrap_servers=config.bootstrap_servers,
            group_id=config.group_id,
            client_id=config.client_id,
            security_protocol=config.security_protocol,
            auto_offset_reset=config.auto_offset_reset,
            sasl_mechanism=config.sasl_mechanism,
            sasl_plain_username=config.sasl_username,
            sasl_plain_password=config.sasl_password,
            enable_auto_commit=True,
        )
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        logger.info("Starting Kafka consumer for topic %s", self._config.topic_upsert)
        await self._consumer.start()
        self._task = asyncio.create_task(self._consume_loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
        await self._consumer.stop()
        logger.info("Kafka consumer stopped")

    async def _consume_loop(self) -> None:
        try:
            async for message in self._consumer:
                payload = self._decode_message(message.value)
                logger.debug("Received vector event: %s", payload)
        except asyncio.CancelledError:
            logger.debug("Kafka consumer task cancelled")

    @staticmethod
    def _decode_message(raw: bytes) -> dict | None:
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            logger.exception("Failed to decode Kafka message")
            return None
