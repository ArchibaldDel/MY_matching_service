from fastapi import Request

from matching_service.config import APIConfig, MLConfig
from matching_service.services.embedder import TextEmbedder
from matching_service.services.vector_cache import VectorCache
from matching_service.storage.repositories import SqliteVectorRepository


def get_cache(request: Request) -> VectorCache:
    return request.app.state.cache


def get_repository(request: Request) -> SqliteVectorRepository:
    return request.app.state.repository


def get_embedder(request: Request) -> TextEmbedder:
    return request.app.state.embedder


def get_api_config(request: Request) -> APIConfig:
    return request.app.state.api_config


def get_ml_config(request: Request) -> MLConfig:
    return request.app.state.ml_config


__all__ = [
    "get_cache",
    "get_repository",
    "get_embedder",
    "get_api_config",
    "get_ml_config",
]

