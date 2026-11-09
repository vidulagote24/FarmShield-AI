"""Health and diagnostics endpoints."""

from typing import Any, Dict
from fastapi import APIRouter, status
from app.core.config import settings
from app.db.session import check_db_connection

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="Health check",
    description="Returns current operational status, version, and database connectivity.",
    status_code=status.HTTP_200_OK,
)
def get_health() -> Dict[str, Any]:
    """Perform health and connectivity check."""
    db_diagnostics = check_db_connection()
    return {
        "status": "healthy" if db_diagnostics.get("connected") else "degraded",
        "app_name": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.APP_ENV,
        "database": db_diagnostics,
    }
