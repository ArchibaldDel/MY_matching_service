from search_service.config.api_config import APIConfig
from search_service.config.db_config import DBConfig
from search_service.config.kafka_config import KafkaConfig
from search_service.config.logging_config import LoggingConfig
from search_service.config.ml_config import MLConfig


class Config:
    def __init__(
        self,
        api_config: APIConfig | None = None,
        db_config: DBConfig | None = None,
        ml_config: MLConfig | None = None,
        logging_config: LoggingConfig | None = None,
        kafka_config: KafkaConfig | None = None,
    ) -> None:
        self.api = api_config or APIConfig()
        self.db = db_config or DBConfig()
        self.ml = ml_config or MLConfig()
        self.logging = logging_config or LoggingConfig()
        self.kafka = kafka_config or KafkaConfig()

    def print_config(self) -> None:
        print("=" * 70)
        print("Configuration Summary:")
        print("=" * 70)
        print(f"API:          {self.api.host}:{self.api.port}")
        print(f"Database:     {self.db.host}:{self.db.port}/{self.db.database}")
        print(f"ML Model:     {self.ml.model_name}")
        print(f"Device:       {self.ml.device or 'auto-detect'}")
        print(f"Vector Dim:   {self.ml.vector_dim}")
        print(f"Max Tokens:   {self.ml.max_text_length}")
        print(f"Log Level:    {self.logging.level}")
        print(f"Kafka topic:  {self.kafka.topic_upsert}")
        print("=" * 70)


__all__ = [
    "Config",
    "APIConfig",
    "DBConfig",
    "MLConfig",
    "LoggingConfig",
    "KafkaConfig",
]

