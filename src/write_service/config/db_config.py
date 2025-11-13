from pydantic import Field

from write_service.config.base import BaseConfig


class DBConfig(BaseConfig):
    """ClickHouse connection settings for the write service."""

    model_config = {"env_prefix": "CH_"}

    host: str = Field(default="localhost", description="ClickHouse host name")
    port: int = Field(default=8123, ge=1, le=65535, description="ClickHouse HTTP port")
    database: str = Field(default="matching", description="Target database name")
    table: str = Field(default="vectors", description="Target table for vector storage")
    username: str = Field(default="default")
    password: str | None = Field(default=None)
    secure: bool = Field(default=False, description="Use TLS for ClickHouse connection")
    timeout: int = Field(default=10, ge=1, le=120, description="Connection & query timeout (seconds)")
    sync_schema: bool = Field(
        default=True,
        description="Auto-create table/vector index on service startup",
    )
    index_name: str = Field(default="idx_vectors_hnsw")
    index_metric: str = Field(
        default="cosine",
        description="Metric used by ClickHouse vector index (cosine|euclidean)",
    )


