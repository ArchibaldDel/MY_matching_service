import logging

import numpy.typing as npt

from matching_service.api.schemas import UpsertResponse
from matching_service.services.embedder import TextEmbedder
from matching_service.services.vector_cache import VectorCache
from matching_service.storage.repositories import SqliteVectorRepository

logger = logging.getLogger(__name__)


def upsert_usecase(
    repository: SqliteVectorRepository,
    cache: VectorCache,
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
    logger.debug("%s vector ID: %s", action.capitalize(), result_id)

    cache.add_or_update(result_id, text, embedding)

    logger.info("Upserted ID: %s (%s)", result_id, action)
    return UpsertResponse(
        id=result_id,
        status="ok",
        message=f"Upserted (ID: {result_id}, {action})",
    )

