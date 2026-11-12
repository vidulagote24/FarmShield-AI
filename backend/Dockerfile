# FarmShield AI Backend - Production Dockerfile
FROM python:3.12-slim-bookworm AS base

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install minimal OS dependencies for PostgreSQL client and healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application code and migration scripts
COPY app ./app
COPY migrations ./migrations
COPY docker ./docker
COPY alembic.ini .

# Create non-root system user for security
RUN groupadd -r farmshield && useradd -r -g farmshield farmshield && \
    chmod +x ./docker/entrypoint.sh && \
    chown -R farmshield:farmshield /app

USER farmshield

# Expose Render default port
EXPOSE 10000

# Container healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT:-10000}/health" || exit 1

# Run Uvicorn ASGI server with dynamic $PORT support (Render defaults to 10000)
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
