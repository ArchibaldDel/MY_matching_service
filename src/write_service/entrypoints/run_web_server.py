import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from write_service.api import setup_exception_handlers
from write_service.api.controllers import health_router, upsert_router
from write_service.config import APIConfig, Config, DBConfig, MLConfig
from write_service.messaging import VectorEventProducer
from write_service.services import TextEmbedder
from write_service.storage.clickhouse_repository import ClickhouseVectorRepository

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    repository: ClickhouseVectorRepository = app.state.repository
    event_producer: VectorEventProducer = app.state.event_producer
    ml_config: MLConfig = app.state.ml_config
    logger.info(
        "Write service starting | model=%s | vectors=%s",
        ml_config.model_name,
        repository.count(),
    )
    try:
        yield
    finally:
        event_producer.flush()
        logger.info("Write service stopped")


def create_app(
    db_config: DBConfig,
    ml_config: MLConfig,
    api_config: APIConfig,
    kafka_config,
) -> FastAPI:
    repository = ClickhouseVectorRepository(db_config)
    event_producer = VectorEventProducer(kafka_config)
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

    app = FastAPI(
        title="Matching Write Service",
        description="Upsert API that embeds products and stores them in ClickHouse",
        version="0.2.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.state.api_config = api_config
    app.state.ml_config = ml_config
    app.state.repository = repository
    app.state.embedder = embedder
    app.state.event_producer = event_producer

    setup_exception_handlers(app)
    app.include_router(health_router, tags=["health"])
    app.include_router(upsert_router, tags=["upsert"])
    return app


def main() -> None:
    config = Config()
    logging.basicConfig(level=getattr(logging, config.logging.level), format=config.logging.format)
    if config.logging.level == "DEBUG":
        config.print_config()
    logger.info("Starting Matching Write Service on %s:%s", config.api.host, config.api.port)
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

