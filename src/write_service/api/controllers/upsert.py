from fastapi import APIRouter, Depends

from write_service.api.schemas import UpsertRequest, UpsertResponse
from write_service.dependencies.providers.services import (
    get_embedder,
    get_event_producer,
    get_ml_config,
    get_repository,
)
from write_service.services.usecases import upsert_usecase

router = APIRouter()


@router.post("/upsert", response_model=UpsertResponse)
def upsert_product(
    payload: UpsertRequest,
    repository=Depends(get_repository),
    event_producer=Depends(get_event_producer),
    embedder=Depends(get_embedder),
    ml_config=Depends(get_ml_config),
) -> UpsertResponse:
    return upsert_usecase(
        repository=repository,
        event_producer=event_producer,
        embedder=embedder,
        vector_id=payload.id,
        text=payload.text,
        embedding_batch_size=ml_config.embedding_batch_size,
    )

