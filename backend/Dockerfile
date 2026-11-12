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

# Expose FastAPI default port
EXPOSE 8000

# Container healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Run entrypoint script handling optional migrations and Uvicorn on dynamic $PORT
CMD ["sh", "./docker/entrypoint.sh"]
