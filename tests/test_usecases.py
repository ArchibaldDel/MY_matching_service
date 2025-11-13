import sys
from types import SimpleNamespace

import numpy as np
import pytest

from write_service.api.schemas import UpsertResponse
from write_service.config.db_config import DBConfig
from write_service.config.kafka_config import KafkaConfig
from write_service.messaging.vector_event_producer import (
    VectorEventProducer,
    VectorUpsertEvent,
)
from write_service.services.usecases.health_usecase import health_usecase
from write_service.services.usecases.upsert_usecase import upsert_usecase
from write_service.storage.clickhouse_repository import ClickhouseVectorRepository


class FakeRepository:
    def __init__(self) -> None:
        self.items: dict[int, tuple[str, np.ndarray]] = {}

    def upsert(self, vector_id: int, text: str, vector: np.ndarray) -> tuple[int, bool]:
        is_new = vector_id not in self.items
        self.items[vector_id] = (text, vector)
        return vector_id, is_new

    def count(self) -> int:
        return len(self.items)


class FakeProducer:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def publish_upsert(self, event) -> None:  # type: ignore[override]
        self.events.append(
            {
                "id": event.id,
                "text": event.text,
                "dim": event.vector_dim,
            }
        )

    def flush(self) -> None:
        pass


class FakeEmbedder:
    embedding_dim = 3

    def encode(self, texts, batch_size, show_progress):  # noqa: D401
        return np.array([[0.1, 0.2, 0.3]], dtype=np.float32)


class DummyMLConfig:
    model_name = "stub"


def test_upsert_success():
    repo = FakeRepository()
    producer = FakeProducer()
    embedder = FakeEmbedder()

    response = upsert_usecase(
        repository=repo,
        event_producer=producer,
        embedder=embedder,
        vector_id=42,
        text="Awesome SKU",
        embedding_batch_size=1,
    )

    assert isinstance(response, UpsertResponse)
    assert response.id == 42
    assert repo.count() == 1
    assert producer.events[0]["id"] == 42
    assert producer.events[0]["dim"] == 3


@pytest.mark.parametrize("bad_text", ["", "   "])
def test_upsert_rejects_empty_text(bad_text):
    repo = FakeRepository()
    producer = FakeProducer()
    embedder = FakeEmbedder()

    with pytest.raises(ValueError):
        upsert_usecase(
            repository=repo,
            event_producer=producer,
            embedder=embedder,
            vector_id=1,
            text=bad_text,
            embedding_batch_size=1,
        )


def test_health_usecase_reflects_repository_state():
    repo = FakeRepository()
    repo.upsert(1, "sku", np.zeros(3, dtype=np.float32))
    response = health_usecase(repository=repo, model_name="model")

    assert response.status == "ok"
    assert response.vectors_count == 1


class FakeResult:
    def __init__(self, rows=None):
        self.result_rows = rows or []


class FakeClickhouseClient:
    def __init__(self):
        self.commands: list[tuple[str, dict | None]] = []
        self.insert_calls: list[tuple[str, list, list[str]]] = []
        self.queries: list[tuple[str, dict | None]] = []
        self.count_rows = 0
        self.existing_ids: set[int] = set()
        self.fail_ping = False

    def command(self, sql: str, parameters: dict | None = None):
        sql_s = sql.strip()
        self.commands.append((sql_s, parameters))
        if sql_s == "SELECT 1" and self.fail_ping:
            raise RuntimeError("ping failed")

    def insert(self, table: str, data: list, column_names: list[str]):
        self.insert_calls.append((table, data, column_names))
        self.count_rows += len(data)
        for row in data:
            self.existing_ids.add(int(row[0]))

    def query(self, sql: str, parameters: dict | None = None):
        sql_s = sql.strip()
        self.queries.append((sql_s, parameters))
        if "count()" in sql_s:
            return FakeResult([[self.count_rows]])
        if "SELECT 1 FROM" in sql_s:
            vector_id = int(parameters["id"])
            return FakeResult([[1]]) if vector_id in self.existing_ids else FakeResult([])
        return FakeResult([])


@pytest.fixture
def fake_clickhouse(monkeypatch) -> FakeClickhouseClient:
    client = FakeClickhouseClient()

    def _get_client(**_kwargs):
        return client

    monkeypatch.setattr(sys.modules["clickhouse_connect"], "get_client", _get_client)
    return client


def test_clickhouse_repository_upsert_and_count(fake_clickhouse: FakeClickhouseClient):
    repo = ClickhouseVectorRepository(DBConfig())

    _, is_new = repo.upsert(100, "SKU", np.array([0.1], dtype=np.float32))
    assert is_new is True
    _, is_new_second = repo.upsert(100, "SKU updated", np.array([0.2], dtype=np.float32))
    assert is_new_second is False

    # Ensure DELETE ran before insert on update.
    assert any("ALTER TABLE" in sql for sql, _ in fake_clickhouse.commands)
    assert repo.count() == 2  # two inserts executed in stub


def test_clickhouse_repository_ping_handles_failure(fake_clickhouse: FakeClickhouseClient):
    repo = ClickhouseVectorRepository(DBConfig())
    fake_clickhouse.fail_ping = True
    assert repo.ping() is False


def test_clickhouse_repository_rejects_invalid_metric(monkeypatch):
    def _get_client(**_):
        return FakeClickhouseClient()

    monkeypatch.setattr(sys.modules["clickhouse_connect"], "get_client", _get_client)
    with pytest.raises(ValueError):
        ClickhouseVectorRepository(DBConfig(index_metric="manhattan"))


def test_vector_event_producer_publishes(monkeypatch):
    messages: list[tuple[str, str, bytes]] = []

    class DummyProducer(SimpleNamespace):
        def __init__(self):
            self.messages = messages

        def produce(self, topic, key, value, on_delivery):
            self.messages.append((topic, key, value))
            on_delivery(None, SimpleNamespace(topic=lambda: topic, partition=lambda: 0))

        def poll(self, timeout):
            pass

        def flush(self):
            pass

    import write_service.messaging.vector_event_producer as producer_module

    monkeypatch.setattr(
        producer_module,
        "Producer",
        lambda *_args, **_kwargs: DummyProducer(),
    )

    producer = VectorEventProducer(KafkaConfig())
    event = VectorUpsertEvent(id=1, text="sku", vector_dim=3, timestamp_ms=123)
    producer.publish_upsert(event)
    assert len(messages) == 1
    assert messages[0][0] == KafkaConfig().topic_upsert


def test_upsert_rejects_non_positive_id():
    repo = FakeRepository()
    producer = FakeProducer()
    embedder = FakeEmbedder()
    with pytest.raises(ValueError):
        upsert_usecase(
            repository=repo,
            event_producer=producer,
            embedder=embedder,
            vector_id=0,
            text="text",
            embedding_batch_size=1,
        )
