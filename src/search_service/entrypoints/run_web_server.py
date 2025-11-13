import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from search_service.api import setup_exception_handlers
from search_service.api.controllers import health_router, search_router
from search_service.config import APIConfig, Config, DBConfig, MLConfig
from search_service.messaging import VectorEventConsumer
from search_service.services import TextEmbedder
from search_service.storage.clickhouse_search import ClickhouseVectorSearcher

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    consumer: VectorEventConsumer = app.state.event_consumer
    searcher: ClickhouseVectorSearcher = app.state.searcher
    ml_config: MLConfig = app.state.ml_config
    logger.info(
        "Search service starting | model=%s | vectors=%s",
        ml_config.model_name,
        searcher.count(),
    )
    await consumer.start()
    try:
        yield
    finally:
        await consumer.stop()
        logger.info("Search service stopped")


def create_app(
    db_config: DBConfig,
    ml_config: MLConfig,
    api_config: APIConfig,
    kafka_config,
) -> FastAPI:
    searcher = ClickhouseVectorSearcher(db_config)
    embedder = TextEmbedder(
        model_name=ml_config.model_name,
        device=ml_config.device,
        max_text_length=ml_config.max_text_length,
        min_clamp_value=ml_config.min_clamp_value,
    )
    if embedder.embedding_dim != ml_config.vector_dim:
        logger.warning(
            "Vector dimension mismatch: config=%d, model=%d",
            ml_config.vector_dim,
            embedder.embedding_dim,
        )
        ml_config.vector_dim = embedder.embedding_dim

    event_consumer = VectorEventConsumer(kafka_config)

    app = FastAPI(
        title="Matching Search Service",
        description="Search API backed by ClickHouse HNSW vectors",
        version="0.2.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.state.api_config = api_config
    app.state.ml_config = ml_config
    app.state.searcher = searcher
    app.state.embedder = embedder
    app.state.event_consumer = event_consumer

    setup_exception_handlers(app)
    app.include_router(health_router, tags=["health"])
    app.include_router(search_router, tags=["search"])
    return app


def main() -> None:
    config = Config()
    logging.basicConfig(level=getattr(logging, config.logging.level), format=config.logging.format)
    if config.logging.level == "DEBUG":
        config.print_config()
    logger.info("Starting Matching Search Service on %s:%s", config.api.host, config.api.port)
    if config.api.reload:
        logger.warning("Auto-reload enabled (development mode - not for production!)")
    app = create_app(
        db_config=config.db,
        ml_config=config.ml,
        api_config=config.api,
        kafka_config=config.kafka,
    )
    uvicorn.run(
        app,
        host=config.api.host,
        port=config.api.port,
        reload=config.api.reload,
        log_level=config.logging.level.lower(),
    )


if __name__ == "__main__":
    main()
