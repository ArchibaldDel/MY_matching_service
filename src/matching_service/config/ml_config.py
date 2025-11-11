class MLConfig:
    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    device: str | None = None
    embedding_batch_size: int = 32
    max_text_length: int = 256
    min_clamp_value: float = 1e-9

