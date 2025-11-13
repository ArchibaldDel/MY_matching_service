from fastapi import Request

from write_service.config import APIConfig, MLConfig
from write_service.messaging import VectorEventProducer
from write_service.services.embedder import TextEmbedder
from write_service.storage.clickhouse_repository import ClickhouseVectorRepository


def get_repository(request: Request) -> ClickhouseVectorRepository:
    return request.app.state.repository


def get_embedder(request: Request) -> TextEmbedder:
    return request.app.state.embedder


def get_api_config(request: Request) -> APIConfig:
    return request.app.state.api_config


def get_ml_config(request: Request) -> MLConfig:
    return request.app.state.ml_config


def get_event_producer(request: Request) -> VectorEventProducer:
    return request.app.state.event_producer


__all__ = [
    "get_repository",
    "get_embedder",
    "get_api_config",
    "get_ml_config",
    "get_event_producer",
]

