import os


class MLConfig:
    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    vector_dim: int = 384
    device: str | None = os.getenv("TORCH_DEVICE", None)
    embedding_batch_size: int = 32
    max_text_length: int = 512
    min_clamp_value: float = 1e-9

