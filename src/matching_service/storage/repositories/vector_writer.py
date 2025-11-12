import logging
import sqlite3
import time

import numpy.typing as npt

from matching_service.storage.repositories.connection import DatabaseConnection
from matching_service.storage.repositories.vector_serializer import VectorSerializer

logger = logging.getLogger(__name__)


class VectorWriter:
    def __init__(self, db_connection: DatabaseConnection) -> None:
        self._db = db_connection
        self._serializer = VectorSerializer()

    def upsert(self, vector_id: int, text: str, vector: npt.NDArray) -> tuple[int, bool]:
        self._validate_upsert_params(vector_id, text, vector)
        try:
            timestamp = int(time.time())
            with self._db.transaction("IMMEDIATE") as conn:
                cursor = conn.cursor()
                exists = self._check_exists(cursor, vector_id)
                
                if exists:
                    self._update_vector(cursor, vector_id, text, vector, timestamp)
                    logger.debug("Updated vector ID: %s", vector_id)
                    return vector_id, False
                else:
                    self._insert_vector(cursor, vector_id, text, vector, timestamp)
                    logger.debug("Inserted vector ID: %s", vector_id)
                    return vector_id, True
        except sqlite3.Error as e:
            logger.error("Failed to upsert vector: %s", e)
            raise RuntimeError(f"Database write error: {e}") from e

    def _validate_upsert_params(self, vector_id: int, text: str, vector: npt.NDArray) -> None:
        if not text.strip():
            raise ValueError("Text cannot be empty")
        if len(vector) == 0:
            raise ValueError("Vector cannot be empty")
        if vector_id <= 0:
            raise ValueError("ID must be positive")

    def _check_exists(self, cursor, vector_id: int) -> bool:
        cursor.execute("SELECT 1 FROM vectors WHERE id = ?", (vector_id,))
        return cursor.fetchone() is not None

    def _update_vector(self, cursor, vector_id: int, text: str, vector: npt.NDArray, timestamp: int) -> None:
        cursor.execute(
            """
            UPDATE vectors 
            SET text = ?, vector = ?, dim = ?, count = count + 1, updated_at = ?
            WHERE id = ?
            """,
            (text, self._serializer.serialize(vector), len(vector), timestamp, vector_id),
        )

    def _insert_vector(self, cursor, vector_id: int, text: str, vector: npt.NDArray, timestamp: int) -> None:
        cursor.execute(
            """
            INSERT INTO vectors (id, text, vector, dim, count, created_at, updated_at)
            VALUES (?, ?, ?, ?, 1, ?, ?)
            """,
            (vector_id, text, self._serializer.serialize(vector), len(vector), timestamp, timestamp),
        )

