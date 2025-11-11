from fastapi import Request

from matching_service.config import APIConfig, MLConfig
from matching_service.services.storage import VectorStorage


def get_storage(request: Request) -> VectorStorage:
    return request.app.state.storage


def get_api_config(request: Request) -> APIConfig:
    return request.app.state.api_config


def get_ml_config(request: Request) -> MLConfig:
    return request.app.state.ml_config


__all__ = [
    "get_storage",
    "get_api_config",
    "get_ml_config",
]

