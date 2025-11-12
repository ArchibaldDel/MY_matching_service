import logging

import numpy.typing as npt

from matching_service.api.schemas import SearchResultItem
from matching_service.services.embedder import TextEmbedder
from matching_service.services.vector_cache import VectorCache

logger = logging.getLogger(__name__)


def search_usecase(
    cache: VectorCache,
    embedder: TextEmbedder,
    text: str,
    top_k: int | None,
    default_top_k: int,
    max_top_k: int,
    score_decimal_places: int,
    embedding_batch_size: int,
) -> list[SearchResultItem]:
    if not text.strip():
        raise ValueError("Query text cannot be empty")

    actual_top_k = top_k or default_top_k
    if actual_top_k > max_top_k:
        raise ValueError(f"top_k must be <= {max_top_k}")

    if cache.is_empty():
        logger.info("Search | len=%s | storage is empty | found=0", len(text))
        return []

    query_embedding: npt.NDArray = embedder.encode(
        [text],
        batch_size=embedding_batch_size,
        show_progress=False,
    )

    scores, indices = cache.search_vectors(query_embedding, actual_top_k)

    results = []
    for score, idx in zip(scores[0], indices[0], strict=False):
        vector_id, vector_text = cache.get_metadata(int(idx))
        results.append(
            SearchResultItem(
                id=vector_id,
                score_rate=round(float(score), score_decimal_places),
                text=vector_text,
            )
        )

    logger.info(
        "Search | len=%s | top_k=%s | found=%s",
        len(text),
        actual_top_k,
        len(results),
    )

    return results

