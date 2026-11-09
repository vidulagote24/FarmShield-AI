"""Business services registry for FarmShield AI."""

from app.services import (
    farm_service,
    irrigation_service,
    observation_service,
    recommendation_service,
    user_service,
    zone_service,
)

__all__ = [
    "user_service",
    "farm_service",
    "zone_service",
    "observation_service",
    "recommendation_service",
    "irrigation_service",
]
