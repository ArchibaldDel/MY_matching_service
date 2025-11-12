from matching_service.api.schemas import HealthResponse
from matching_service.services.vector_cache import VectorCache


def health_usecase(cache: VectorCache, model_name: str) -> HealthResponse:
    return HealthResponse(
        status="ok",
        message="Service is running",
        model=model_name,
        vectors_count=cache.count(),
    )

