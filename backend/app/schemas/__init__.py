"""Pydantic schemas registry for FarmShield AI."""

from app.schemas.common import BaseSchema, PaginatedResponse
from app.schemas.auth import (
    LoginRequest,
    TokenPayload,
    TokenResponse,
    UserRegisterRequest,
)
from app.schemas.farm import (
    FarmBase,
    FarmBoundaryResponse,
    FarmBoundaryUpdate,
    FarmCreate,
    FarmResponse,
    FarmUpdate,
    FarmZoneBase,
    FarmZoneCreate,
    FarmZoneResponse,
    FarmZoneUpdate,
)
from app.schemas.irrigation import (
    IrrigationEventBase,
    IrrigationEventCreate,
    IrrigationEventResponse,
    IrrigationEventUpdate,
)
from app.schemas.observation import (
    ObservationBase,
    ObservationCreate,
    ObservationResponse,
)
from app.schemas.recommendation import (
    RecommendationBase,
    RecommendationCreate,
    RecommendationResponse,
    RecommendationStatusUpdate,
    RecommendationUpdate,
)
from app.schemas.user import (
    FarmerProfileBase,
    FarmerProfileCreate,
    FarmerProfileResponse,
    FarmerProfileUpdate,
    UserBase,
    UserCreate,
    UserResponse,
    UserUpdate,
)

# Preserve Health and ServiceInfo schemas from Part 1
from app.schemas.common import BaseSchema
from typing import Any, Dict


class HealthResponse(BaseSchema):
    """Schema for health check response."""

    status: str
    app_name: str
    version: str
    environment: str
    database: Dict[str, Any]


class ServiceInfoResponse(BaseSchema):
    """Schema for root endpoint response."""

    app_name: str
    version: str
    status: str
    docs_url: str
    redoc_url: str
    api_prefix: str


__all__ = [
    "BaseSchema",
    "PaginatedResponse",
    "HealthResponse",
    "ServiceInfoResponse",
    # Auth & Tokens
    "UserRegisterRequest",
    "LoginRequest",
    "TokenResponse",
    "TokenPayload",
    # User & Farmer Profile
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "FarmerProfileBase",
    "FarmerProfileCreate",
    "FarmerProfileUpdate",
    "FarmerProfileResponse",
    # Farm & Zone
    "FarmBase",
    "FarmCreate",
    "FarmUpdate",
    "FarmBoundaryUpdate",
    "FarmBoundaryResponse",
    "FarmResponse",
    "FarmZoneBase",
    "FarmZoneCreate",
    "FarmZoneUpdate",
    "FarmZoneResponse",
    # Observation
    "ObservationBase",
    "ObservationCreate",
    "ObservationResponse",
    # Recommendation
    "RecommendationBase",
    "RecommendationCreate",
    "RecommendationUpdate",
    "RecommendationStatusUpdate",
    "RecommendationResponse",
    # Irrigation
    "IrrigationEventBase",
    "IrrigationEventCreate",
    "IrrigationEventUpdate",
    "IrrigationEventResponse",
]
