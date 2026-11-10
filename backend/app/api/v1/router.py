"""API Version 1 Router aggregating all domain endpoint routers."""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    farms,
    health,
    ingestion,
    irrigation,
    observations,
    recommendations,
    users,
    zones,
)

api_router = APIRouter()

# Register endpoint routers
api_router.include_router(auth.router)
api_router.include_router(health.router)
api_router.include_router(users.router)
api_router.include_router(farms.router)
api_router.include_router(zones.router)
api_router.include_router(observations.router)
api_router.include_router(recommendations.router)
api_router.include_router(irrigation.router)
api_router.include_router(ingestion.router)
