from fastapi.testclient import TestClient
import numpy as np
import pytest

from write_service.config import APIConfig, DBConfig, MLConfig, KafkaConfig
from write_service.entrypoints.run_web_server import create_app
import write_service.storage.clickhouse_repository as ch_repo
import write_service.messaging.vector_event_producer as producer_module
import write_service.services.embedder as embedder_module
import write_service.entrypoints.run_web_server as app_module


class FakeRepo:
    def __init__(self):
        self.items = {}

    def upsert(self, vector_id, text, vector):
        is_new = vector_id not in self.items
        self.items[vector_id] = (text, vector)
        return vector_id, is_new

    def count(self):
        return len(self.items)


class FakeProducer:
    def __init__(self):
        self.events = []

    def publish_upsert(self, event):
        self.events.append(event)

    def flush(self):
        pass


class FakeEmbedder:
    embedding_dim = 3

    def encode(self, texts, batch_size, show_progress):
        return np.array([[0.1, 0.2, 0.3]], dtype=np.float32)


@pytest.fixture
def api_app(monkeypatch):
    fake_repo = FakeRepo()
    fake_producer = FakeProducer()
    fake_embedder = FakeEmbedder()

    monkeypatch.setattr(ch_repo, "ClickhouseVectorRepository", lambda config: fake_repo)
    monkeypatch.setattr(app_module, "ClickhouseVectorRepository", lambda config: fake_repo)
    monkeypatch.setattr(producer_module, "VectorEventProducer", lambda config: fake_producer)
    monkeypatch.setattr(app_module, "VectorEventProducer", lambda config: fake_producer)
    monkeypatch.setattr(embedder_module, "TextEmbedder", lambda **kwargs: fake_embedder)
    monkeypatch.setattr(app_module, "TextEmbedder", lambda **kwargs: fake_embedder)

    app = create_app(
        db_config=DBConfig(),
        ml_config=MLConfig(),
        api_config=APIConfig(),
        kafka_config=KafkaConfig(),
    )

    app.state.repository = fake_repo
    app.state.event_producer = fake_producer
    app.state.embedder = fake_embedder

    return app


def test_upsert_endpoint(api_app):
    client = TestClient(api_app)
    response = client.post(
        "/upsert",
        json={"id": 123, "text": "Test SKU"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == 123
    assert payload["status"] == "ok"


def test_health_endpoint(api_app):
    client = TestClient(api_app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
