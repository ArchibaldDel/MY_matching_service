import logging
import time

import numpy.typing as npt

from write_service.api.schemas import UpsertResponse
from write_service.messaging import VectorEventProducer
from write_service.messaging.vector_event_producer import VectorUpsertEvent
from write_service.services.embedder import TextEmbedder
from write_service.storage.clickhouse_repository import ClickhouseVectorRepository

logger = logging.getLogger(__name__)


def upsert_usecase(
    repository: ClickhouseVectorRepository,
    event_producer: VectorEventProducer,
    embedder: TextEmbedder,
    vector_id: int,
    text: str,
    embedding_batch_size: int,
) -> UpsertResponse:
    if not text.strip():
        raise ValueError("Text cannot be empty")
    if vector_id <= 0:
        raise ValueError("ID must be positive")

    embedding: npt.NDArray = embedder.encode(
        [text], batch_size=embedding_batch_size, show_progress=False
    )[0]

    result_id, is_new = repository.upsert(vector_id, text, embedding)
    action = "inserted" if is_new else "updated"
    logger.info("Upserted ID: %s (%s)", result_id, action)

    event = VectorUpsertEvent(
        id=result_id,
        text=text,
        vector_dim=int(embedding.shape[0]),
        timestamp_ms=int(time.time() * 1000),
    )
    event_producer.publish_upsert(event)

    return UpsertResponse(
        id=result_id,
        status="ok",
        message=f"Upserted (ID: {result_id}, {action})",
    )


