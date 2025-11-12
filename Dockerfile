# syntax=docker/dockerfile:1

# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /build

# Install uv (one time only)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy only dependency files first (better caching)
COPY pyproject.toml uv.lock* ./

# Install dependencies in isolated layer
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Copy source code and install project
COPY src/ src/
COPY README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Replace PyTorch with CPU-only version (saves ~2GB vs CUDA version)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --force-reinstall --no-deps \
    torch==2.5.1+cpu \
    --index-url https://download.pytorch.org/whl/cpu


# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install minimal runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && \
    useradd -r -g appuser -u 1000 -m -d /app appuser && \
    mkdir -p /app/data /app/.cache && \
    chown -R appuser:appuser /app

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser /build/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appuser src/ /app/src/
COPY --chown=appuser:appuser pyproject.toml README.md /app/

# Switch to non-root user
USER appuser

# Environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    TORCH_HOME=/app/.cache/torch

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Default command
CMD ["matching-service", "--host", "0.0.0.0", "--port", "8000"]

