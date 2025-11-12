from fastapi import APIRouter, Depends
from fastapi.responses import Response
from matching_service.api.schemas import HealthResponse
from matching_service.dependencies.providers.services import (
    get_cache,
    get_ml_config,
)
from matching_service.services.usecases import health_usecase

router = APIRouter()


@router.get("/", response_model=HealthResponse)
def health_check(
    cache=Depends(get_cache),
    ml_config=Depends(get_ml_config),
) -> HealthResponse:
    return health_usecase(cache=cache, model_name=ml_config.model_name)


@router.head("/")
def health_check_head() -> Response:
    return Response(status_code=200)
