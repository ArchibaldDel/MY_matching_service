import logging
from typing import Annotated
from fastapi import APIRouter, Query, Request
from matching_service.api.error_handlers import handle_service_errors
from matching_service.api.schemas import SearchResultItem
from matching_service.services.storage import SearchResultDTO

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/search", response_model=list[SearchResultItem])
@handle_service_errors
def search_similar_products(
    request: Request,
    text: Annotated[str, Query(min_length=1, max_length=2000)],
    top_k: Annotated[int | None, Query(ge=1)] = None,
) -> list[SearchResultItem]:
    storage = request.app.state.storage
    cfg = request.app.state.config
    actual_top_k = top_k or cfg.default_top_k
    if actual_top_k > cfg.max_top_k:
        raise ValueError(f"top_k must be <= {cfg.max_top_k}")

    results: list[SearchResultDTO] = storage.search(
        query_text=text, top_k=actual_top_k
    )
    logger.info(
        "Search | len=%s | top_k=%s | found=%s",
        len(text),
        actual_top_k,
        len(results),
    )

    response_results: list[SearchResultItem] = [
        SearchResultItem(
            id=dto.id,
            score_rate=round(dto.score, cfg.score_decimal_places),
            text=dto.text,
        )
        for dto in results
    ]

    return response_results
