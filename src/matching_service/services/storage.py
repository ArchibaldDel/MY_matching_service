import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

import numpy as np
import numpy.typing as npt

from matching_service.services.search import cosine_topk
from matching_service.utils.exceptions import (
    EmptyStorageError,
    InvalidTextError,
)

if TYPE_CHECKING:
    from matching_service.services.embedder import TextEmbedder
    from matching_service.storage.repositories.sqlite_repository import (
        SqliteVectorRepository,
    )

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchResultDTO:
    id: int
    score: float
    text: str


class VectorStorage:
    def __init__(
        self,
        repository: "SqliteVectorRepository",
        embedding_batch_size: int,
        embedder: Optional["TextEmbedder"] = None,
    ) -> None:
        self.repository: SqliteVectorRepository = repository
        self.embedder: TextEmbedder | None = embedder
        self._embedding_batch_size: int = embedding_batch_size
        self.embeddings: npt.NDArray[np.float32] | None = None
        self._ids: list[int] = []
        self._texts: list[str] = []
        self._load_vectors_from_db()
        logger.info("VectorStorage initialized | vectors=%s", self.count())

    def _require_embedder(self) -> "TextEmbedder":
        if not self.embedder:
            raise RuntimeError("Embedder not initialized")
        return self.embedder

    def _load_vectors_from_db(self) -> None:
        (
            self._ids,
            self._texts,
            self.embeddings,
        ) = self.repository.get_all_vectors()

    def upsert(self, text: str) -> int:
        if not text.strip():
            raise InvalidTextError("Text cannot be empty")
        embedder = self._require_embedder()

        embedding: npt.NDArray[np.float32] = embedder.encode(
            [text], batch_size=self._embedding_batch_size, show_progress=False
        )[0]

        existing = self.repository.get_by_text(text)
        if existing:
            vector_id = self.repository.update(text, embedding)
            logger.debug("Updated existing vector ID: %s", vector_id)
        else:
            vector_id = self.repository.insert(text, embedding)
            logger.debug("Inserted new vector ID: %s", vector_id)

        self._load_vectors_from_db()
        return vector_id

    def search(self, query_text: str, top_k: int) -> list[SearchResultDTO]:
        if not query_text.strip():
            raise InvalidTextError("Query text cannot be empty")
        if self.embeddings is None or self.count() == 0:
            raise EmptyStorageError("Storage is empty")
        embedder = self._require_embedder()

        query_embedding: npt.NDArray[np.float32] = embedder.encode(
            [query_text],
            batch_size=self._embedding_batch_size,
            show_progress=False,
        )
        actual_top_k: int = min(top_k, self.count())
        scores, indices = cosine_topk(query_embedding, self.embeddings, actual_top_k)

        results: list[SearchResultDTO] = [
            SearchResultDTO(
                id=self._ids[int(idx)],
                score=float(score),
                text=self._texts[int(idx)],
            )
            for score, idx in zip(scores[0], indices[0], strict=False)
        ]
        logger.debug("Search found %s results", len(results))
        return results

    def count(self) -> int:
        return len(self._ids)
