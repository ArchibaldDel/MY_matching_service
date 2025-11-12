import logging
import sqlite3

import numpy as np
import numpy.typing as npt

from matching_service.storage.repositories.connection import DatabaseConnection
from matching_service.storage.repositories.vector_serializer import VectorSerializer

logger = logging.getLogger(__name__)


class VectorReader:
    def __init__(self, db_connection: DatabaseConnection) -> None:
        self._db = db_connection
        self._serializer = VectorSerializer()

    def get_all_vectors(self) -> tuple[list[int], list[str], npt.NDArray[np.float32]]:
        try:
            with self._db.read_transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, text, vector, dim FROM vectors ORDER BY id")
                rows = cursor.fetchall()
                if not rows:
                    empty_array: npt.NDArray[np.float32] = np.array([], dtype=np.float32)
                    return [], [], empty_array
                ids: list[int] = []
                texts: list[str] = []
                vectors: list[npt.NDArray[np.float32]] = []
                for row_id, text, vector_blob, dim in rows:
                    ids.append(row_id)
                    texts.append(text)
                    vectors.append(self._serializer.deserialize(vector_blob, dim))
                stacked_vectors: npt.NDArray[np.float32] = np.stack(vectors).astype(np.float32)
                logger.debug("Retrieved %d vectors from storage", len(ids))
                return ids, texts, stacked_vectors
        except sqlite3.Error as e:
            logger.error("Failed to get all vectors: %s", e)
            raise RuntimeError(f"Database read error: {e}") from e

