import logging
import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import uvicorn
from fastapi import FastAPI

from matching_service.api import setup_exception_handlers
from matching_service.api.controllers import (
    health_router,
    search_router,
    upsert_router,
)
from matching_service.config import APIConfig, Config, DBConfig, MLConfig
from matching_service.services import TextEmbedder
from matching_service.services.vector_cache import VectorCache
from matching_service.storage.repositories import SqliteVectorRepository

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    ml_config: MLConfig = app.state.ml_config
    cache: VectorCache = app.state.cache
    repository: SqliteVectorRepository = app.state.repository

    logger.info(
        "Service starting | Model: %s | Vectors: %s",
        ml_config.model_name,
        f"{cache.count():,}",
    )

    yield

    repository.close()
    logger.info("Service shutting down - database connection closed")


def create_app(
    db_config: DBConfig,
    ml_config: MLConfig,
    api_config: APIConfig,
) -> FastAPI:
    repository = SqliteVectorRepository(db_path=str(db_config.vector_db_path))

    embedder = TextEmbedder(
        model_name=ml_config.model_name,
        device=ml_config.device,
        max_text_length=ml_config.max_text_length,
        min_clamp_value=ml_config.min_clamp_value,
    )
    
    if embedder.embedding_dim != ml_config.vector_dim:
        logger.warning(
            "Vector dimension mismatch: config=%d, model=%d. Using model dimension.",
            ml_config.vector_dim,
            embedder.embedding_dim,
        )
        ml_config.vector_dim = embedder.embedding_dim

    cache = VectorCache(vector_dim=ml_config.vector_dim)
    ids, texts, vectors = repository.get_all_vectors()
    cache.load_all(ids, texts, vectors)
    logger.info("Cache initialized with %s vectors", cache.count())

    app = FastAPI(
        title="Product Matching Service",
        description="Векторный поиск похожих товаров",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.state.api_config = api_config
    app.state.ml_config = ml_config
    app.state.cache = cache
    app.state.repository = repository
    app.state.embedder = embedder

    setup_exception_handlers(app)

    app.include_router(health_router, tags=["health"])
    app.include_router(search_router, tags=["search"])
    app.include_router(upsert_router, tags=["upsert"])

    return app


def main() -> None:
    config = Config()
    
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    
    host = os.getenv("API_HOST", config.api.api_host)
    port = int(os.getenv("API_PORT", config.api.api_port))
    reload = os.getenv("API_RELOAD", "false").lower() == "true"
    
    logger.info("Starting Matching Service on %s:%s", host, port)
    if reload:
        logger.info("Auto-reload enabled (development mode)")
    
    app = create_app(
        db_config=config.db,
        ml_config=config.ml,
        api_config=config.api,
    )
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_level=log_level.lower(),
    )


if __name__ == "__main__":
    main()
