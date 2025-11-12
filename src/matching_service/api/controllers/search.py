from typing import Annotated
from fastapi import APIRouter, Query, Depends
from matching_service.api.schemas import SearchResultItem
from matching_service.dependencies.providers.services import (
    get_api_config,
    get_cache,
    get_embedder,
    get_ml_config,
)
from matching_service.services.usecases import search_usecase

router = APIRouter()


@router.get("/search", response_model=list[SearchResultItem])
def search_similar_products(
    text: Annotated[str, Query(min_length=1, max_length=2000)],
    top_k: Annotated[int | None, Query(ge=1)] = None,
    cache=Depends(get_cache),
    embedder=Depends(get_embedder),
    api_config=Depends(get_api_config),
    ml_config=Depends(get_ml_config),
) -> list[SearchResultItem]:
    return search_usecase(
        cache=cache,
        embedder=embedder,
        text=text,
        top_k=top_k,
        default_top_k=api_config.default_top_k,
        max_top_k=api_config.max_top_k,
        score_decimal_places=api_config.score_decimal_places,
        embedding_batch_size=ml_config.embedding_batch_size,
    )
