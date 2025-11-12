import logging
import threading

import numpy as np
import numpy.typing as npt

logger = logging.getLogger(__name__)


class VectorCache:
    def __init__(self, initial_capacity: int = 10000, vector_dim: int = 384) -> None:
        self._capacity = initial_capacity
        self._size = 0
        self._vector_dim = vector_dim
        self._ids: list[int] = []
        self._texts: list[str] = []
        self._vectors = np.zeros((initial_capacity, vector_dim), dtype=np.float32)
        self._id_to_index: dict[int, int] = {}
        self._lock = threading.RLock()
        logger.debug("VectorCache initialized with capacity=%s, dim=%s", initial_capacity, vector_dim)

    def load_all(
        self,
        ids: list[int],
        texts: list[str],
        vectors: npt.NDArray[np.float32],
    ) -> None:
        with self._lock:
            num_vectors = len(ids)
            
            if num_vectors == 0:
                self._clear_cache()
                logger.debug("Cache loaded: 0 vectors (empty)")
                return
            
            self._validate_vector_dimension(vectors)
            self._ensure_capacity(num_vectors)
            self._populate_cache(ids, texts, vectors, num_vectors)
            logger.debug("Cache loaded: %s vectors", num_vectors)

    def _clear_cache(self) -> None:
        self._ids = []
        self._texts = []
        self._size = 0
        self._id_to_index = {}

    def _validate_vector_dimension(self, vectors: npt.NDArray[np.float32]) -> None:
        if vectors.shape[1] != self._vector_dim:
            raise ValueError(
                f"Vector dimension mismatch: expected {self._vector_dim}, got {vectors.shape[1]}. "
                f"Database was created with a different model. Delete data/vectors.db and restart."
            )

    def _ensure_capacity(self, required: int) -> None:
        if required > self._capacity:
            new_capacity = max(required, self._capacity * 2)
            self._vectors = np.zeros((new_capacity, self._vector_dim), dtype=np.float32)
            self._capacity = new_capacity
            logger.debug("Cache expanded to capacity=%s", new_capacity)

    def _populate_cache(
        self,
        ids: list[int],
        texts: list[str],
        vectors: npt.NDArray[np.float32],
        num_vectors: int,
    ) -> None:
        self._ids = ids.copy()
        self._texts = texts.copy()
        self._vectors[:num_vectors] = vectors
        self._size = num_vectors
        self._id_to_index = {vector_id: idx for idx, vector_id in enumerate(ids)}

    def add_or_update(
        self, vector_id: int, text: str, vector: npt.NDArray[np.float32]
    ) -> None:
        if len(vector) != self._vector_dim:
            raise ValueError(
                f"Vector dimension mismatch: expected {self._vector_dim}, got {len(vector)}"
            )
        
        with self._lock:
            if vector_id in self._id_to_index:
                idx = self._id_to_index[vector_id]
                self._texts[idx] = text
                self._vectors[idx] = vector
                logger.debug("Cache updated: ID=%s", vector_id)
            else:
                if self._size >= self._capacity:
                    self._expand()
                
                idx = self._size
                self._id_to_index[vector_id] = idx
                self._ids.append(vector_id)
                self._texts.append(text)
                self._vectors[idx] = vector
                self._size += 1
                logger.debug("Cache added: ID=%s (size=%s/%s)", vector_id, self._size, self._capacity)

    def _expand(self) -> None:
        new_capacity = self._capacity * 2
        new_vectors = np.zeros((new_capacity, self._vector_dim), dtype=np.float32)
        new_vectors[:self._size] = self._vectors[:self._size]
        self._vectors = new_vectors
        self._capacity = new_capacity
        logger.info("Cache expanded to capacity=%s", new_capacity)

    def search_vectors(
        self,
        query_vector: npt.NDArray[np.float32],
        top_k: int,
    ) -> tuple[npt.NDArray[np.float32], npt.NDArray[np.int32]]:
        with self._lock:
            if self._size == 0:
                empty_scores = np.array([], dtype=np.float32).reshape(1, 0)
                empty_indices = np.array([], dtype=np.int32).reshape(1, 0)
                return empty_scores, empty_indices
            
            corpus_vectors = self._vectors[:self._size]
            sims: npt.NDArray[np.float32] = query_vector @ corpus_vectors.T
            
            if sims.ndim == 1:
                sims = sims.reshape(1, -1)
            
            actual_k = min(top_k, self._size)
            idx: npt.NDArray[np.int32] = np.argsort(-sims, axis=1)[:, :actual_k].astype(np.int32)
            batch_indices: npt.NDArray[np.int32] = np.arange(sims.shape[0], dtype=np.int32)[:, np.newaxis]
            scores: npt.NDArray[np.float32] = sims[batch_indices, idx]
            
            return scores, idx

    def get_metadata(self, idx: int) -> tuple[int, str]:
        with self._lock:
            if idx >= self._size:
                raise IndexError(f"Index {idx} out of range (size={self._size})")
            return self._ids[idx], self._texts[idx]

    def is_empty(self) -> bool:
        with self._lock:
            return self._size == 0

    def count(self) -> int:
        with self._lock:
            return self._size

