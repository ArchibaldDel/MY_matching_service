import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import click
import uvicorn
from fastapi import FastAPI

from matching_service.api import setup_exception_handlers
from matching_service.api.controllers import (
    health_router,
    search_router,
    upsert_router,
)
from matching_service.config import APIConfig, Config, DBConfig, MLConfig
from matching_service.services import TextEmbedder, VectorStorage
from matching_service.storage.repositories import SqliteVectorRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    ml_config: MLConfig = app.state.ml_config
    storage: VectorStorage = app.state.storage

    logger.info(
        "Service starting | Model: %s | Vectors: %s",
        ml_config.model_name,
        f"{storage.count():,}",
    )

    yield

    storage.repository.close()
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

    storage = VectorStorage(
        repository=repository,
        embedding_batch_size=ml_config.embedding_batch_size,
        embedder=embedder,
    )

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
    app.state.storage = storage

    setup_exception_handlers(app)

    app.include_router(health_router, tags=["health"])
    app.include_router(search_router, tags=["search"])
    app.include_router(upsert_router, tags=["upsert"])

    return app


@click.command()
@click.option(
    "--host",
    default=None,
    help="API host address (default: from config)",
    show_default=True,
)
@click.option(
    "--port",
    default=None,
    type=int,
    help="API port (default: from config)",
    show_default=True,
)
@click.option(
    "--reload",
    is_flag=True,
    default=False,
    help="Enable auto-reload for development",
)
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    help="Logging level",
    show_default=True,
)
def cli(
    host: str | None,
    port: int | None,
    reload: bool,
    log_level: str,
) -> None:
    config = Config()

    if host is None:
        host = config.api.api_host
    if port is None:
        port = config.api.api_port

    logging.getLogger().setLevel(getattr(logging, log_level.upper()))

    click.echo(f"Starting Matching Service on {host}:{port}")
    if reload:
        click.echo("Auto-reload enabled (development mode)")

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
    cli()
