from pydantic import Field

from matching_service.config.base import BaseConfig


class APIConfig(BaseConfig):
    model_config = {"env_prefix": "API_"}

    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000, ge=1, le=65535)
    reload: bool = Field(default=False)
    default_top_k: int = Field(default=5, ge=1, le=100)
    max_top_k: int = Field(default=50, ge=1, le=1000)
    score_decimal_places: int = Field(default=4, ge=0, le=10)

