import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import click
import uvicorn
from fastapi import FastAPI

from matching_service.api.controllers import (
    health_router,
    search_router,
    upsert_router,
)
from matching_service.config import Config
from matching_service.services import TextEmbedder, VectorStorage
from matching_service.storage.repositories import SqliteVectorRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    cfg: Config = app.state.config
    storage: VectorStorage = app.state.storage

    logger.info("=" * 70)
    logger.info(
        "Service starting | Model: %s | Vectors: %s",
        cfg.model_name,
        f"{storage.count():,}",
    )
    logger.info("=" * 70)

    yield

    storage.repository.close()
    logger.info("Service shutting down - database connection closed")


def create_app(cfg: Config) -> FastAPI:
    repository = SqliteVectorRepository(db_path=str(cfg.vector_db_path))

    embedder = TextEmbedder(
        model_name=cfg.model_name,
        device=cfg.device,
        max_text_length=cfg.max_text_length,
        min_clamp_value=cfg.min_clamp_value,
    )

    storage = VectorStorage(
        repository=repository,
        embedding_batch_size=cfg.embedding_batch_size,
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

    app.state.config = cfg
    app.state.storage = storage

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
    cfg = Config()

    if host is None:
        host = cfg.api_host
    if port is None:
        port = cfg.api_port

    logging.getLogger().setLevel(getattr(logging, log_level.upper()))

    click.echo(f"Starting Matching Service on {host}:{port}")
    if reload:
        click.echo("Auto-reload enabled (development mode)")

    app = create_app(cfg)

    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_level=log_level.lower(),
    )


if __name__ == "__main__":
    cli()
