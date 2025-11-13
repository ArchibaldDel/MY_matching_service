# Matching Write Service

Write-side FastAPI application that embeds product cards and upserts vectors into ClickHouse, emitting Kafka events for downstream consumers.

## Quick start

```bash
pip install uv
uv sync
uv run matching-write-service
```

To run locally with ClickHouse + Kafka:

```bash
docker compose up --build
```

Use `.env.sample` as a reference for required configuration.
