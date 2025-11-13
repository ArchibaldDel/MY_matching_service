from pydantic import Field, field_validator

from matching_service.config.base import BaseConfig


class MLConfig(BaseConfig):
    model_config = {"env_prefix": "ML_"}

    model_name: str = Field(default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    vector_dim: int = Field(default=384, ge=1, le=4096)
    device: str | None = Field(default=None, description="cpu, cuda, auto, or None for auto-detect")
    embedding_batch_size: int = Field(default=32, ge=1, le=512)
    max_text_length: int = Field(default=512, ge=1, le=8192)
    min_clamp_value: float = Field(default=1e-9, gt=0)

    @field_validator("device")
    @classmethod
    def validate_device(cls, v: str | None) -> str | None:
        if v is not None and v.lower() not in ("cpu", "cuda", "auto"):
            raise ValueError("device must be 'cpu', 'cuda', 'auto', or None")
        return v.lower() if v else None

