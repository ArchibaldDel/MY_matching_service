from fastapi import APIRouter, Depends
from fastapi.responses import Response

from search_service.api.schemas import HealthResponse
from search_service.dependencies.providers.services import (
    get_ml_config,
    get_searcher,
)
from search_service.services.usecases import health_usecase

router = APIRouter()


@router.get("/", response_model=HealthResponse)
def health_check(
    searcher=Depends(get_searcher),
    ml_config=Depends(get_ml_config),
) -> HealthResponse:
    return health_usecase(searcher=searcher, model_name=ml_config.model_name)


@router.head("/")
def health_check_head() -> Response:
    return Response(status_code=200)
