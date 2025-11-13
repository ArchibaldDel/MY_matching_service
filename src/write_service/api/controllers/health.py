from fastapi import APIRouter, Depends
from fastapi.responses import Response

from write_service.api.schemas import HealthResponse
from write_service.dependencies.providers.services import (
    get_ml_config,
    get_repository,
)
from write_service.services.usecases import health_usecase

router = APIRouter()


@router.get("/", response_model=HealthResponse)
def health_check(
    repository=Depends(get_repository),
    ml_config=Depends(get_ml_config),
) -> HealthResponse:
    return health_usecase(repository=repository, model_name=ml_config.model_name)


@router.head("/")
def health_check_head() -> Response:
    return Response(status_code=200)

