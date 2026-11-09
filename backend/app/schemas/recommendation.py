"""Pydantic schemas for Recommendation records."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import Field, field_validator
from app.schemas.common import BaseSchema

VALID_PRIORITIES = {"low", "medium", "high", "critical"}
VALID_STATUSES = {
    "pending",
    "applied",
    "dismissed",
    "expired",
    "accepted",
    "rejected",
    "completed",
}


class RecommendationBase(BaseSchema):
    """Base fields for Recommendation."""

    recommendation_type: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    priority: str = Field("medium", max_length=50)
    status: str = Field("pending", max_length=50)
    reasoning: Dict[str, Any] = Field(default_factory=dict)
    recommended_action: Dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    valid_until: Optional[datetime] = None

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in VALID_PRIORITIES:
            raise ValueError(f"Priority must be one of: {sorted(list(VALID_PRIORITIES))}")
        return clean

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in VALID_STATUSES:
            raise ValueError(f"Status must be one of: {sorted(list(VALID_STATUSES))}")
        return clean


class RecommendationCreate(RecommendationBase):
    """Payload for creating a new Recommendation."""

    farm_id: Optional[uuid.UUID] = None
    zone_id: Optional[uuid.UUID] = None


class RecommendationUpdate(BaseSchema):
    """Payload for modifying a Recommendation."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    priority: Optional[str] = None
    status: Optional[str] = None
    reasoning: Optional[Dict[str, Any]] = None
    recommended_action: Optional[Dict[str, Any]] = None
    valid_until: Optional[datetime] = None

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip().lower()
            if clean not in VALID_PRIORITIES:
                raise ValueError(f"Priority must be one of: {sorted(list(VALID_PRIORITIES))}")
            return clean
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip().lower()
            if clean not in VALID_STATUSES:
                raise ValueError(f"Status must be one of: {sorted(list(VALID_STATUSES))}")
            return clean
        return v


class RecommendationStatusUpdate(BaseSchema):
    """Payload for updating the status of a Recommendation (e.g. accepted, rejected, completed)."""

    status: str = Field(..., description="Target status: pending, accepted, rejected, or completed.")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in VALID_STATUSES:
            raise ValueError(f"Status must be one of: {sorted(list(VALID_STATUSES))}")
        return clean


class RecommendationResponse(RecommendationBase):
    """Response representation of a Recommendation."""

    id: uuid.UUID
    farm_id: uuid.UUID
    zone_id: Optional[uuid.UUID] = None
    created_at: datetime
