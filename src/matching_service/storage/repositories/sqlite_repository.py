import logging
import sqlite3
import time
from types import TracebackType

import numpy as np
import numpy.typing as npt

logger = logging.getLogger(__name__)


class SqliteVectorRepository:
    def __init__(self, db_path: str = "vectors.db") -> None:
        self._conn: sqlite3.Connection = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()
        logger.info("SqliteVectorRepository connected to %s", db_path)

    def _create_tables(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vectors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT UNIQUE,
                vector BLOB NOT NULL,
                dim INTEGER NOT NULL,
                count INTEGER NOT NULL DEFAULT 1,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_text ON vectors(text)")
        self._conn.commit()

    def _serialize_vector(self, vector: npt.NDArray[np.float32]) -> bytes:
        return vector.astype(np.float32).tobytes()

    def _deserialize_vector(self, blob: bytes, dim: int) -> npt.NDArray[np.float32]:
        return np.frombuffer(blob, dtype=np.float32).reshape(dim)

    def get_by_text(self, text: str) -> tuple[int, npt.NDArray[np.float32]] | None:
        try:
            cursor = self._conn.cursor()
            cursor.execute("SELECT id, vector, dim FROM vectors WHERE text = ?", (text,))
            row = cursor.fetchone()
            if row:
                vector_id, vector_blob, dim = row
                vector = self._deserialize_vector(vector_blob, dim)
                return (vector_id, vector)
            return None
        except sqlite3.Error as e:
            logger.error("Database error: %s", e)
            raise sqlite3.Error(f"Database error: {e}")

    def insert(self, text: str, vector: npt.NDArray[np.float32]) -> int:
        if not text.strip() or len(vector) == 0:
            raise ValueError("Text and vector cannot be empty")

        try:
            timestamp = int(time.time())
            cursor = self._conn.cursor()
            cursor.execute(
                """
                INSERT INTO vectors (
                    text, vector, dim, count, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    text,
                    self._serialize_vector(vector),
                    len(vector),
                    1,
                    timestamp,
                    timestamp,
                ),
            )
            self._conn.commit()
            vector_id = cursor.lastrowid
            logger.debug("Inserted vector ID: %s", vector_id)
            return vector_id
        except sqlite3.Error as e:
            self._conn.rollback()
            logger.error("Database error: %s", e)
            raise sqlite3.Error(f"Database error: {e}")

    def update(self, text: str, vector: npt.NDArray[np.float32]) -> int:
        if not text.strip() or len(vector) == 0:
            raise ValueError("Text and vector cannot be empty")

        try:
            timestamp = int(time.time())
            cursor = self._conn.cursor()
            cursor.execute(
                """
                UPDATE vectors 
                SET vector = ?, dim = ?, count = count + 1, updated_at = ?
                WHERE text = ?
            """,
                (
                    self._serialize_vector(vector),
                    len(vector),
                    timestamp,
                    text,
                ),
            )
            self._conn.commit()
            cursor.execute("SELECT id FROM vectors WHERE text = ?", (text,))
            row = cursor.fetchone()
            if row:
                vector_id = row[0]
                logger.debug("Updated vector ID: %s", vector_id)
                return vector_id
            raise ValueError(f"Vector with text '{text}' not found")
        except sqlite3.Error as e:
            self._conn.rollback()
            logger.error("Database error: %s", e)
            raise sqlite3.Error(f"Database error: {e}")

    def batch_insert(
        self,
        texts: list[str],
        vectors: npt.NDArray[np.float32],
        batch_size: int,
    ) -> None:
        if len(texts) != len(vectors):
            raise ValueError(f"Length mismatch: {len(texts)} vs {len(vectors)}")

        timestamp = int(time.time())
        try:
            for i in range(0, len(texts), batch_size):
                data = [
                    (
                        text,
                        self._serialize_vector(vector),
                        len(vector),
                        1,
                        timestamp,
                        timestamp,
                    )
                    for text, vector in zip(
                        texts[i : i + batch_size],
                        vectors[i : i + batch_size],
                    )
                    if text.strip()
                ]
                if data:
                    self._conn.executemany(
                        """
                        INSERT OR IGNORE INTO vectors (
                            text, vector, dim, count, created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        data,
                    )
                    self._conn.commit()
                    logger.debug("Batch inserted %s vectors", len(data))
        except sqlite3.Error as e:
            self._conn.rollback()
            logger.error("Batch insert error: %s", e)
            raise sqlite3.Error(f"Batch insert error: {e}")

    def get_all_vectors(
        self,
    ) -> tuple[list[int], list[str], npt.NDArray[np.float32]]:
        try:
            rows: list[tuple] = self._conn.execute(
                "SELECT id, text, vector, dim FROM vectors ORDER BY id"
            ).fetchall()

            if not rows:
                empty_array: npt.NDArray[np.float32] = np.array([], dtype=np.float32)
                return [], [], empty_array

            ids: list[int] = []
            texts: list[str] = []
            vectors: list[npt.NDArray[np.float32]] = []

            for row_id, text, vector_blob, dim in rows:
                ids.append(row_id)
                texts.append(text)
                vectors.append(self._deserialize_vector(vector_blob, dim))

            stacked_vectors: npt.NDArray[np.float32] = np.stack(vectors).astype(np.float32)
            return ids, texts, stacked_vectors
        except sqlite3.Error as e:
            logger.error("Load vectors error: %s", e)
            raise sqlite3.Error(f"Load vectors error: {e}")

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM vectors").fetchone()[0]

    def close(self) -> None:
        self._conn.close()
        logger.info("Database connection closed")

    def __enter__(self) -> "SqliteVectorRepository":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()
