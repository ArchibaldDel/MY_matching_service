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
# Skip on ARM64 (Apple Silicon) to avoid compatibility issues
RUN --mount=type=cache,target=/root/.cache/pip \
    if [ "$(uname -m)" = "x86_64" ]; then \
        pip install --force-reinstall --no-deps \
        torch==2.5.1+cpu \
        --index-url https://download.pytorch.org/whl/cpu; \
    else \
        echo "Skipping CPU-only PyTorch on ARM64 - using default version"; \
    fi


# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install minimal runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

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

# Metadata
LABEL org.opencontainers.image.title="Matching Service"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.description="Vector-based product matching service"

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Default command (arguments ignored, use ENV variables instead)
CMD ["matching-service"]

