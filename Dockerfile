
# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN chmod +x /usr/local/bin/uv

# Copy project files needed for build
COPY pyproject.toml uv.lock* README.md ./
COPY src/ src/

# Install dependencies
RUN uv sync --frozen --no-dev


# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install wget for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN chmod +x /usr/local/bin/uv

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY src/ src/
COPY pyproject.toml README.md ./

# Create data directory
RUN mkdir -p data

# Use uv's Python environment
ENV PATH="/app/.venv/bin:$PATH"

# Expose port
EXPOSE 8000

# Default command
CMD ["matching-service", "--host", "0.0.0.0", "--port", "8000"]

