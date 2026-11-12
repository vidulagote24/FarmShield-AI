#!/bin/sh
set -e

# Run database migrations if RUN_MIGRATIONS is true or 1 (default: true)
if [ "${RUN_MIGRATIONS:-true}" = "true" ] || [ "${RUN_MIGRATIONS:-true}" = "1" ]; then
    echo "[Railway Entrypoint] Checking and running database migrations (alembic upgrade head)..."
    alembic upgrade head
    echo "[Railway Entrypoint] Database migrations applied successfully."
fi

# Execute Uvicorn replacing the shell process for proper POSIX signal handling
echo "[Railway Entrypoint] Starting Uvicorn on 0.0.0.0:${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
