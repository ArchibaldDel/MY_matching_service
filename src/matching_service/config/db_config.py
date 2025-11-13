from pathlib import Path

from pydantic import Field, field_validator

from matching_service.config.base import BaseConfig


class DBConfig(BaseConfig):
    model_config = {"env_prefix": "DB_"}

    vector_db_path: Path = Field(default=Path("data/vectors.db"))

    @field_validator("vector_db_path")
    @classmethod
    def ensure_parent_dir(cls, v: Path) -> Path:
        v.parent.mkdir(parents=True, exist_ok=True)
        return v

