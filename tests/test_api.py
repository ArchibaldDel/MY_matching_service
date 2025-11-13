import numpy as np
from fastapi.testclient import TestClient
import pytest

from search_service.config import APIConfig, DBConfig, MLConfig, KafkaConfig
from search_service.entrypoints.run_web_server import create_app
import search_service.storage.clickhouse_search as search_module
import search_service.messaging.vector_event_consumer as consumer_module
import search_service.services.embedder as embedder_module


class FakeSearcher:
    def __init__(self):
        self.rows = [
            {"id": 1, "text": "SKU 1", "score": 0.9},
            {"id": 2, "text": "SKU 2", "score": 0.8},
        ]

    def search(self, vector, top_k):
        return self.rows[:top_k]

    def count(self):
        return len(self.rows)

    def ping(self):
        return True


class FakeConsumer:
    def __init__(self):
        self.started = False
        self.stopped = False

    async def start(self):
        self.started = True

    async def stop(self):
        self.stopped = True


class FakeEmbedder:
    embedding_dim = 3

    def encode(self, texts, batch_size, show_progress):
        return np.array([[0.1, 0.2, 0.3]], dtype=np.float32)


@pytest.fixture
def api_app(monkeypatch):
    fake_searcher = FakeSearcher()
    fake_consumer = FakeConsumer()
    fake_embedder = FakeEmbedder()

    monkeypatch.setattr(
        search_module,
        "ClickhouseVectorSearcher",
        lambda config: fake_searcher,
    )
    monkeypatch.setattr(
        consumer_module,
        "VectorEventConsumer",
        lambda config: fake_consumer,
    )
    monkeypatch.setattr(
        embedder_module,
        "TextEmbedder",
        lambda **kwargs: fake_embedder,
    )

    app = create_app(
        db_config=DBConfig(),
        ml_config=MLConfig(),
        api_config=APIConfig(),
        kafka_config=KafkaConfig(),
    )
    app.state.searcher = fake_searcher
    app.state.event_consumer = fake_consumer
    app.state.embedder = fake_embedder
    return app


def test_search_endpoint(api_app):
    client = TestClient(api_app)
    response = client.get("/search", params={"text": "ELM327", "top_k": 2})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["score_rate"] == pytest.approx(0.9, rel=1e-3)


def test_health_endpoint(api_app):
    client = TestClient(api_app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["vectors_count"] == 2
