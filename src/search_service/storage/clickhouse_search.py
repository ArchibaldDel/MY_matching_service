from __future__ import annotations

import logging
from typing import Any

import clickhouse_connect
import numpy as np
import numpy.typing as npt

from search_service.config.db_config import DBConfig

logger = logging.getLogger(__name__)


class ClickhouseVectorSearcher:
    """Executes vector similarity queries in ClickHouse."""

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
        self._max_limit = config.max_search_limit
        logger.info("Connected to ClickHouse search table %s.%s", config.database, self._table)

    def search(self, query_vector: npt.NDArray[np.float32], top_k: int) -> list[dict[str, Any]]:
        top_k = min(top_k, self._max_limit)
        query_vector = query_vector.astype(np.float32).tolist()
        metric = self._config.index_metric.lower()
        if metric == "cosine":
            distance_expr = "1 - vectorCosineDistance(vector, %(query)s)"
        elif metric == "euclidean":
            distance_expr = "1 / (1 + sqrt(vectorL2SquaredDistance(vector, %(query)s)))"
        else:
            raise ValueError("index_metric must be 'cosine' or 'euclidean'")

        sql = f"""
            SELECT id, text, {distance_expr} AS score
            FROM {self._table}
            ORDER BY score DESC
            LIMIT %(limit)s
        """
        result = self._client.query(
            sql,
            parameters={
                "query": query_vector,
                "limit": top_k,
            },
        )
        records: list[dict[str, Any]] = []
        for row in result.named_results():
            records.append(
                {
                    "id": row["id"],
                    "text": row["text"],
                    "score": float(row["score"]),
                }
            )
        return records

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
