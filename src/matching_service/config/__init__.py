from matching_service.config.api_config import APIConfig
from matching_service.config.constants import Constants
from matching_service.config.db_config import DBConfig
from matching_service.config.ml_config import MLConfig


class Config:
    def __init__(
        self,
        db_config: DBConfig | None = None,
        ml_config: MLConfig | None = None,
        api_config: APIConfig | None = None,
        constants: Constants | None = None,
    ) -> None:
        self.db = db_config or DBConfig()
        self.ml = ml_config or MLConfig()
        self.api = api_config or APIConfig()
        self.constants = constants or Constants()
        self._setup_compatibility()
    
    def _setup_compatibility(self) -> None:
        self.vector_db_path = self.db.vector_db_path
        self.model_name = self.ml.model_name
        self.device = self.ml.device
        self.embedding_batch_size = self.ml.embedding_batch_size
        self.max_text_length = self.ml.max_text_length
        self.min_clamp_value = self.ml.min_clamp_value
        self.api_host = self.api.api_host
        self.api_port = self.api.api_port
        self.default_top_k = self.api.default_top_k
        self.max_top_k = self.api.max_top_k
        self.score_decimal_places = self.api.score_decimal_places
        self.data_path = self.constants.data_path


__all__ = [
    "Config",
    "DBConfig",
    "MLConfig",
    "APIConfig",
    "Constants",
]

