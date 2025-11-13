from pydantic import Field, field_validator

from write_service.config.base import BaseConfig


class LoggingConfig(BaseConfig):
    model_config = {"env_prefix": "LOG_"}

    level: str = Field(default="INFO")
    format: str = Field(default="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        allowed_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        v_upper = v.upper()
        if v_upper not in allowed_levels:
            raise ValueError(f"level must be one of: {', '.join(allowed_levels)}")
        return v_upper

    @property
    def level_upper(self) -> str:
        return self.level.upper()


