from fastapi import Request

from search_service.config import APIConfig, MLConfig
from search_service.services.embedder import TextEmbedder
from search_service.storage.clickhouse_search import ClickhouseVectorSearcher


def get_searcher(request: Request) -> ClickhouseVectorSearcher:
    return request.app.state.searcher


def get_embedder(request: Request) -> TextEmbedder:
    return request.app.state.embedder


def get_api_config(request: Request) -> APIConfig:
    return request.app.state.api_config


def get_ml_config(request: Request) -> MLConfig:
    return request.app.state.ml_config


__all__ = [
    "get_searcher",
    "get_embedder",
    "get_api_config",
    "get_ml_config",
]
