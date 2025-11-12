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

    def insert(self, vector_id: int, text: str, vector: npt.NDArray) -> int:
        if not text.strip():
            raise ValueError("Text cannot be empty")
        if len(vector) == 0:
            raise ValueError("Vector cannot be empty")
        if vector_id <= 0:
            raise ValueError("ID must be positive")
        try:
            timestamp = int(time.time())
            with self._db.transaction("IMMEDIATE") as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO vectors (id, text, vector, dim, count, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 1, ?, ?)
                    """,
                    (
                        vector_id,
                        text,
                        self._serializer.serialize(vector),
                        len(vector),
                        timestamp,
                        timestamp,
                    ),
                )
                logger.debug("Inserted vector ID: %s", vector_id)
                return vector_id
        except sqlite3.IntegrityError as e:
            logger.error("Vector with ID %s already exists", vector_id)
            raise ValueError(f"Vector with ID {vector_id} already exists") from e
        except sqlite3.Error as e:
            logger.error("Failed to insert vector: %s", e)
            raise RuntimeError(f"Database write error: {e}") from e

    def update(self, vector_id: int, text: str, vector: npt.NDArray) -> int:
        if not text.strip():
            raise ValueError("Text cannot be empty")
        if len(vector) == 0:
            raise ValueError("Vector cannot be empty")
        if vector_id <= 0:
            raise ValueError("ID must be positive")
        try:
            timestamp = int(time.time())
            with self._db.transaction("IMMEDIATE") as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE vectors 
                    SET text = ?, vector = ?, dim = ?, count = count + 1, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        text,
                        self._serializer.serialize(vector),
                        len(vector),
                        timestamp,
                        vector_id,
                    ),
                )
                if cursor.rowcount == 0:
                    raise ValueError(f"Vector with ID {vector_id} not found")
                logger.debug("Updated vector ID: %s", vector_id)
                return vector_id
        except sqlite3.Error as e:
            logger.error("Failed to update vector: %s", e)
            raise RuntimeError(f"Database write error: {e}") from e

    def upsert(self, vector_id: int, text: str, vector: npt.NDArray) -> tuple[int, bool]:
        if not text.strip():
            raise ValueError("Text cannot be empty")
        if len(vector) == 0:
            raise ValueError("Vector cannot be empty")
        if vector_id <= 0:
            raise ValueError("ID must be positive")
        try:
            timestamp = int(time.time())
            with self._db.transaction("IMMEDIATE") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM vectors WHERE id = ?", (vector_id,))
                exists = cursor.fetchone() is not None
                if exists:
                    cursor.execute(
                        """
                        UPDATE vectors 
                        SET text = ?, vector = ?, dim = ?, count = count + 1, updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            text,
                            self._serializer.serialize(vector),
                            len(vector),
                            timestamp,
                            vector_id,
                        ),
                    )
                    logger.debug("Updated vector ID: %s", vector_id)
                    return vector_id, False
                else:
                    cursor.execute(
                        """
                        INSERT INTO vectors (id, text, vector, dim, count, created_at, updated_at)
                        VALUES (?, ?, ?, ?, 1, ?, ?)
                        """,
                        (
                            vector_id,
                            text,
                            self._serializer.serialize(vector),
                            len(vector),
                            timestamp,
                            timestamp,
                        ),
                    )
                    logger.debug("Inserted vector ID: %s", vector_id)
                    return vector_id, True
        except sqlite3.Error as e:
            logger.error("Failed to upsert vector: %s", e)
            raise RuntimeError(f"Database write error: {e}") from e

    def delete(self, text: str) -> bool:
        try:
            with self._db.transaction("IMMEDIATE") as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM vectors WHERE text = ?", (text,))
                deleted = cursor.rowcount > 0
                if deleted:
                    logger.debug("Deleted vector with text: %s", text)
                return deleted
        except sqlite3.Error as e:
            logger.error("Failed to delete vector: %s", e)
            raise RuntimeError(f"Database write error: {e}") from e

    def batch_insert(
        self, ids: list[int], texts: list[str], vectors: npt.NDArray, batch_size: int = 100
    ) -> list[int]:
        if len(ids) != len(texts) or len(texts) != len(vectors):
            raise ValueError(
                f"Length mismatch: {len(ids)} ids, {len(texts)} texts, {len(vectors)} vectors"
            )
        inserted_ids: list[int] = []
        timestamp = int(time.time())
        try:
            with self._db.transaction("IMMEDIATE") as conn:
                for i in range(0, len(ids), batch_size):
                    batch_ids = ids[i : i + batch_size]
                    batch_texts = texts[i : i + batch_size]
                    batch_vectors = vectors[i : i + batch_size]
                    data = [
                        (
                            vector_id,
                            text,
                            self._serializer.serialize(vector),
                            len(vector),
                            1,
                            timestamp,
                            timestamp,
                        )
                        for vector_id, text, vector in zip(
                            batch_ids, batch_texts, batch_vectors, strict=False
                        )
                        if text.strip() and vector_id > 0
                    ]
                    if data:
                        conn.executemany(
                            """
                            INSERT OR REPLACE INTO vectors 
                            (id, text, vector, dim, count, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            data,
                        )
                        inserted_ids.extend([row[0] for row in data])
                        logger.debug("Batch inserted %d vectors", len(data))
                logger.info("Batch insert completed: %d vectors", len(inserted_ids))
                return inserted_ids
        except sqlite3.Error as e:
            logger.error("Batch insert error: %s", e)
            raise RuntimeError(f"Batch insert error: {e}") from e

