from fastapi import APIRouter, Depends
from matching_service.api.schemas import UpsertRequest, UpsertResponse
from matching_service.dependencies.providers.services import (
    get_cache,
    get_embedder,
    get_ml_config,
    get_repository,
)
from matching_service.services.usecases import upsert_usecase

router = APIRouter()


@router.post("/upsert", response_model=UpsertResponse)
def upsert_product(
    payload: UpsertRequest,
    repository=Depends(get_repository),
    cache=Depends(get_cache),
    embedder=Depends(get_embedder),
    ml_config=Depends(get_ml_config),
) -> UpsertResponse:
    return upsert_usecase(
        repository=repository,
        cache=cache,
        embedder=embedder,
        vector_id=payload.id,
        text=payload.text,
        embedding_batch_size=ml_config.embedding_batch_size,
    )
