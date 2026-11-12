"""Health and diagnostics endpoints."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Response, status
from app.core.config import settings
from app.db.session import check_db_connection

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="Health check",
    description="Returns current operational status, version, and database connectivity.",
    status_code=status.HTTP_200_OK,
)
def get_health(response: Response = None) -> Dict[str, Any]:
    """Perform health and connectivity check."""
    db_diagnostics = check_db_connection()
    is_healthy = bool(
        db_diagnostics.get("connected") and db_diagnostics.get("postgis_installed")
    )
    if not is_healthy and response is not None:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "healthy" if is_healthy else "degraded",
        "app_name": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.APP_ENV,
        "database": db_diagnostics,
    }
