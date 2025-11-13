import logging

import numpy.typing as npt

from search_service.api.schemas import SearchResultItem
from search_service.services.embedder import TextEmbedder
from search_service.storage.clickhouse_search import ClickhouseVectorSearcher

logger = logging.getLogger(__name__)


def search_usecase(
    searcher: ClickhouseVectorSearcher,
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

    actual_top_k = min(top_k or default_top_k, max_top_k)

    query_embedding: npt.NDArray = embedder.encode(
        [text],
        batch_size=embedding_batch_size,
        show_progress=False,
    )

    rows = searcher.search(query_embedding[0], actual_top_k)

    results = [
        SearchResultItem(
            id=int(row["id"]),
            score_rate=round(float(row["score"]), score_decimal_places),
            text=row["text"],
        )
        for row in rows
    ]

    logger.info(
        "Search | len=%s | top_k=%s | found=%s",
        len(text),
        actual_top_k,
        len(results),
    )

    return results

