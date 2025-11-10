from matching_service.api.controllers.health import router as health_router
from matching_service.api.controllers.search import router as search_router
from matching_service.api.controllers.upsert import router as upsert_router

__all__ = ["health_router", "search_router", "upsert_router"]
