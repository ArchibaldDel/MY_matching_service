import logging
from fastapi import APIRouter, Depends
from matching_service.api.schemas import UpsertRequest, UpsertResponse
from matching_service.dependencies.providers.services import get_storage
from matching_service.services.usecases import upsert_usecase

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upsert", response_model=UpsertResponse)
def upsert_product(
    payload: UpsertRequest,
    storage=Depends(get_storage),
) -> UpsertResponse:
    data = upsert_usecase(storage=storage, text=payload.text)
    return UpsertResponse(**data)
