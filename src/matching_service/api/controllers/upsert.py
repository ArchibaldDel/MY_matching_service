import logging
from fastapi import APIRouter, Request
from matching_service.api.error_handlers import handle_service_errors
from matching_service.api.schemas import UpsertRequest, UpsertResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upsert", response_model=UpsertResponse)
@handle_service_errors
def upsert_product(
    request: Request,
    payload: UpsertRequest,
) -> UpsertResponse:
    storage = request.app.state.storage
    vector_id: int = storage.upsert(payload.text)
    logger.info("Upserted ID: %s", vector_id)
    return UpsertResponse(
        id=vector_id,
        status="ok",
        message="Upserted (ID: %s)" % vector_id,
    )
