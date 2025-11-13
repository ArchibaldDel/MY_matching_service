from write_service.api.schemas import HealthResponse
from write_service.storage.clickhouse_repository import ClickhouseVectorRepository


def health_usecase(repository: ClickhouseVectorRepository, model_name: str) -> HealthResponse:
    return HealthResponse(
        status="ok",
        message="Service is running",
        model=model_name,
        vectors_count=repository.count(),
    )


