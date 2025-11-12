from matching_service.config.api_config import APIConfig
from matching_service.config.db_config import DBConfig
from matching_service.config.ml_config import MLConfig


class Config:
    def __init__(
        self,
        db_config: DBConfig | None = None,
        ml_config: MLConfig | None = None,
        api_config: APIConfig | None = None,
    ) -> None:
        self.db = db_config or DBConfig()
        self.ml = ml_config or MLConfig()
        self.api = api_config or APIConfig()


__all__ = [
    "Config",
    "DBConfig",
    "MLConfig",
    "APIConfig",
]

