import logging
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from matching_service.api.schemas import HealthResponse
from matching_service.dependencies.providers.services import (
    get_ml_config,
    get_storage,
)
from matching_service.services.usecases import health_usecase

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=HealthResponse)
def health_check(
    storage=Depends(get_storage),
    ml_config=Depends(get_ml_config),
) -> HealthResponse:
    data = health_usecase(storage=storage, model_name=ml_config.model_name)
    return HealthResponse(**data)


@router.head("/")
def health_check_head() -> Response:
    return Response(status_code=200)
