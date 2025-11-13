from pydantic import Field

from search_service.config.base import BaseConfig


class DBConfig(BaseConfig):
    """ClickHouse search connection settings."""

    model_config = {"env_prefix": "CH_"}

    host: str = Field(default="localhost")
    port: int = Field(default=9000, ge=1, le=65535)
    database: str = Field(default="matching")
    table: str = Field(default="vectors")
    username: str = Field(default="default")
    password: str | None = Field(default=None)
    secure: bool = Field(default=False)
    timeout: int = Field(default=10, ge=1, le=120)
    index_metric: str = Field(default="cosine")
    max_search_limit: int = Field(default=100, ge=1, le=1000)

