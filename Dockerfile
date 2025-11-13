# syntax=docker/dockerfile:1

FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv

RUN python -m venv $VIRTUAL_ENV && \
    apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip && pip install .

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app/src:$PYTHONPATH" \
    HF_HOME=/app/.cache/huggingface

RUN groupadd -r app && useradd -r -g app app && mkdir -p /app /app/.cache/huggingface && chown -R app:app /app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/README.md /app/

WORKDIR /app
USER app

EXPOSE 8001

CMD ["matching-write-service"]
