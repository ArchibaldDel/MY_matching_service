import logging
from fastapi import APIRouter, Request
from matching_service.api.schemas import HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=HealthResponse)
def health_check(request: Request) -> HealthResponse:
    storage = request.app.state.storage
    cfg = request.app.state.config
    return HealthResponse(
        status="ok",
        message="Service is running",
        model=cfg.model_name,
        vectors_count=storage.count(),
    )
