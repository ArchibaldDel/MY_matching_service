from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import clickhouse_connect
import numpy as np
import numpy.typing as npt

from write_service.config.db_config import DBConfig

logger = logging.getLogger(__name__)


class ClickhouseVectorRepository:
    """Stores vectors in ClickHouse and keeps the table/index in sync."""

    def __init__(self, config: DBConfig) -> None:
        self._config = config
        self._client = clickhouse_connect.get_client(
            host=config.host,
            port=config.port,
            username=config.username,
            password=config.password or "",
            database=config.database,
            secure=config.secure,
            connect_timeout=config.timeout,
            send_receive_timeout=config.timeout,
        )
        self._table = config.table
        if config.sync_schema:
            self._ensure_schema()

    def _ensure_schema(self) -> None:
        logger.info("Ensuring ClickHouse table %s.%s exists", self._config.database, self._table)
        self._client.command(
            f"""
            CREATE TABLE IF NOT EXISTS {self._table} (
                id UInt64,
                text String,
                vector Array(Float32),
                dim UInt16,
                count UInt32,
                created_at DateTime64(3),
                updated_at DateTime64(3)
            )
            ENGINE = MergeTree
            ORDER BY id
            """
        )
        # Try to create vector index (HNSW syntax may not be supported in all ClickHouse versions)
        index_metric = self._config.index_metric.lower()
        if index_metric not in {"cosine", "euclidean"}:
            raise ValueError("index_metric must be 'cosine' or 'euclidean'")
        try:
            self._client.command(
                f"""
                CREATE VECTOR INDEX IF NOT EXISTS {self._config.index_name}
                ON {self._table} (vector)
                TYPE hnsw('metric_type={index_metric}')
                """
            )
            logger.info("Vector index %s created successfully", self._config.index_name)
        except Exception as e:
            logger.warning(
                "Failed to create vector index %s: %s. "
                "Table will work without index (slower on large datasets)",
                self._config.index_name,
                e,
            )

    def upsert(self, vector_id: int, text: str, vector: npt.NDArray[np.float32]) -> tuple[int, bool]:
        vector = vector.astype(np.float32)
        dim = vector.shape[0]
        now = datetime.now(timezone.utc)
        exists = self._exists(vector_id)
        if exists:
            logger.debug("Replacing vector ID %s in ClickHouse", vector_id)
            self._client.command(
                f"ALTER TABLE {self._table} DELETE WHERE id = %(id)s",
                parameters={"id": vector_id},
            )
        data = [
            (
                vector_id,
                text,
                vector.tolist(),
                dim,
                1,
                now,
                now,
            )
        ]
        self._client.insert(
            self._table,
            data,
            column_names=["id", "text", "vector", "dim", "count", "created_at", "updated_at"],
        )
        return vector_id, not exists

    def _exists(self, vector_id: int) -> bool:
        result = self._client.query(
            f"SELECT 1 FROM {self._table} WHERE id = %(id)s LIMIT 1",
            parameters={"id": vector_id},
        )
        return bool(result.result_rows)

    def count(self) -> int:
        result = self._client.query(f"SELECT count() FROM {self._table}")
        return int(result.result_rows[0][0]) if result.result_rows else 0

    def ping(self) -> bool:
        try:
            self._client.command("SELECT 1")
            return True
        except Exception:
            logger.exception("ClickHouse ping failed")
            return False

