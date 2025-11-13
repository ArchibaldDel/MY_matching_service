import asyncio
import json
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from search_service.api.schemas import SearchResultItem
from search_service.config.db_config import DBConfig
from search_service.config.kafka_config import KafkaConfig
from search_service.messaging.vector_event_consumer import VectorEventConsumer
from search_service.services.usecases.health_usecase import health_usecase
from search_service.services.usecases.search_usecase import search_usecase
from search_service.storage.clickhouse_search import ClickhouseVectorSearcher


class FakeSearcher:
    def __init__(self) -> None:
        self.rows = [
            {"id": 1, "text": "SKU 1", "score": 0.95},
            {"id": 2, "text": "SKU 2", "score": 0.90},
        ]

    def search(self, query_vector, top_k):
        return self.rows[:top_k]

    def count(self) -> int:
        return len(self.rows)


class FakeEmbedder:
    embedding_dim = 3

    def encode(self, texts, batch_size, show_progress):
        return np.array([[0.1, 0.2, 0.3]], dtype=np.float32)


def test_search_returns_clickhouse_rows():
    searcher = FakeSearcher()
    embedder = FakeEmbedder()

    results = search_usecase(
        searcher=searcher,
        embedder=embedder,
        text="ELM327",
        top_k=5,
        default_top_k=2,
        max_top_k=10,
        score_decimal_places=3,
        embedding_batch_size=4,
    )

    assert len(results) == 2
    assert all(isinstance(item, SearchResultItem) for item in results)
    assert results[0].score_rate == pytest.approx(0.95, rel=1e-3)


def test_search_trims_top_k_to_limit():
    searcher = FakeSearcher()
    embedder = FakeEmbedder()

    results = search_usecase(
        searcher=searcher,
        embedder=embedder,
        text="ELM327",
        top_k=100,
        default_top_k=1,
        max_top_k=1,
        score_decimal_places=2,
        embedding_batch_size=1,
    )

    assert len(results) == 1


def test_search_rejects_empty_text():
    searcher = FakeSearcher()
    embedder = FakeEmbedder()

    with pytest.raises(ValueError):
        search_usecase(
            searcher=searcher,
            embedder=embedder,
            text="  ",
            top_k=None,
            default_top_k=5,
            max_top_k=10,
            score_decimal_places=2,
            embedding_batch_size=1,
        )


def test_health_usecase_reads_clickhouse_count():
    searcher = FakeSearcher()
    response = health_usecase(searcher=searcher, model_name="model")
    assert response.vectors_count == len(searcher.rows)


class FakeQueryResult:
    def __init__(self, rows=None, named=None):
        self.result_rows = rows or []
        self._named = named or []

    def named_results(self):
        return self._named


class FakeSearchClient:
    def __init__(self):
        self.queries: list[tuple[str, dict | None]] = []
        self.commands: list[str] = []
        self.count_rows = 4
        self.named_rows = [
            {"id": 11, "text": "SKU 11", "score": 0.77},
        ]
        self.fail_ping = False

    def query(self, sql: str, parameters: dict | None = None):
        sql_s = sql.strip()
        self.queries.append((sql_s, parameters))
        if "count()" in sql_s:
            return FakeQueryResult([[self.count_rows]])
        return FakeQueryResult(named=self.named_rows)

    def command(self, sql: str):
        if sql.strip() == "SELECT 1" and self.fail_ping:
            raise RuntimeError("clickhouse unreachable")
        self.commands.append(sql.strip())


@pytest.fixture
def fake_search_client(monkeypatch) -> FakeSearchClient:
    client = FakeSearchClient()

    def _get_client(**_):
        return client

    monkeypatch.setattr(sys.modules["clickhouse_connect"], "get_client", _get_client)
    return client


def test_clickhouse_searcher_executes_queries(fake_search_client: FakeSearchClient):
    config = DBConfig()
    searcher = ClickhouseVectorSearcher(config)
    results = searcher.search(
        np.array([0.1, 0.2], dtype=np.float32),
        top_k=config.max_search_limit + 5,
    )
    assert results[0]["id"] == 11
    assert fake_search_client.queries[-1][1]["limit"] == config.max_search_limit


def test_clickhouse_searcher_invalid_metric(monkeypatch):
    def _get_client(**_):
        return FakeSearchClient()

    monkeypatch.setattr(sys.modules["clickhouse_connect"], "get_client", _get_client)
    searcher = ClickhouseVectorSearcher(DBConfig(index_metric="cosine"))
    # change config afterwards to invalid and call search to trigger branch
    searcher._config.index_metric = "manhattan"
    with pytest.raises(ValueError):
        searcher.search(np.ones(2, dtype=np.float32), top_k=1)


def test_clickhouse_searcher_ping_handles_failure(fake_search_client: FakeSearchClient):
    searcher = ClickhouseVectorSearcher(DBConfig())
    fake_search_client.fail_ping = True
    assert searcher.ping() is False


def test_vector_event_consumer_start_stop():
    consumer = VectorEventConsumer(KafkaConfig())
    stub = consumer._consumer

    async def runner():
        await consumer.start()
        assert stub.started is True
        await consumer.stop()
        assert stub.stopped is True

    asyncio.run(runner())


def test_vector_event_consumer_decode_error():
    assert VectorEventConsumer._decode_message(b"{") is None


def test_vector_event_consumer_decode_success():
    payload = {"id": 1, "text": "sku"}
    data = json.dumps(payload).encode("utf-8")
    assert VectorEventConsumer._decode_message(data) == payload
