from pathlib import Path


class Config:
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    data_path: Path = Path("data/KE_Автотовары.jsonl")
    vector_db_path: Path = Path("data/vectors.db")

    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    device: str | None = None

    default_top_k: int = 5
    max_top_k: int = 50
    embedding_batch_size: int = 32
    max_text_length: int = 256
    min_clamp_value: float = 1e-9
    score_decimal_places: int = 4
