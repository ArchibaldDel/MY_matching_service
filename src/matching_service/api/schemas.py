from pydantic import BaseModel, Field, field_validator


class UpsertRequest(BaseModel):
    id: int = Field(
        ...,
        description="Уникальный идентификатор товара",
        gt=0,
        examples=[12345],
    )
    text: str = Field(
        ...,
        description="Текстовая карточка товара",
        min_length=1,
        max_length=100000,
        examples=["Диагностический адаптер ELM327 Bluetooth OBD2"],
    )

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Текст не может быть пустым")
        return v.strip()


class UpsertResponse(BaseModel):
    id: int = Field(..., gt=0)
    status: str
    message: str


class SearchResultItem(BaseModel):
    id: int = Field(..., gt=0)
    score_rate: float = Field(..., ge=-1.0, le=1.0)
    text: str = Field(..., min_length=1)


class HealthResponse(BaseModel):
    status: str
    message: str
    model: str
    vectors_count: int
