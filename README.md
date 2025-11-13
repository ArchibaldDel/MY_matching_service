# Matching Search Service

Search-side FastAPI application that queries ClickHouse HNSW vectors and exposes a `/search` endpoint plus health checks. A Kafka consumer is included for future cache warm-up.

## Quick start

```bash
pip install uv
uv sync
uv run matching-search-service
```

With Docker Compose (ClickHouse + Kafka):

```bash
docker compose up --build
```

Use `.env.sample` as a reference for configuration.
