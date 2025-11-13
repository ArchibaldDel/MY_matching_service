from search_service.api.schemas import HealthResponse
from search_service.storage.clickhouse_search import ClickhouseVectorSearcher


def health_usecase(searcher: ClickhouseVectorSearcher, model_name: str) -> HealthResponse:
    return HealthResponse(
        status="ok",
        message="Service is running",
        model=model_name,
        vectors_count=searcher.count(),
    )

