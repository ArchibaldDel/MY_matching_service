import logging

import numpy.typing as npt

from matching_service.api.schemas import SearchResultItem
from matching_service.services.embedder import TextEmbedder
from matching_service.services.search import cosine_topk
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
        raise ValueError("Storage is empty")

    query_embedding: npt.NDArray = embedder.encode(
        [text],
        batch_size=embedding_batch_size,
        show_progress=False,
    )

    corpus_vectors = cache.get_vectors()
    actual_top_k = min(actual_top_k, cache.count())

    scores, indices = cosine_topk(query_embedding, corpus_vectors, actual_top_k)

    results = [
        SearchResultItem(
            id=cache.get_metadata(int(idx))[0],
            score_rate=round(float(score), score_decimal_places),
            text=cache.get_metadata(int(idx))[1],
        )
        for score, idx in zip(scores[0], indices[0], strict=False)
    ]

    logger.info(
        "Search | len=%s | top_k=%s | found=%s",
        len(text),
        actual_top_k,
        len(results),
    )

    return results

