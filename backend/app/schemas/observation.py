"""Pydantic schemas for Observation records."""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import Field, field_validator, model_validator
from app.schemas.common import BaseSchema

VALID_OBSERVATION_TYPES = {
    "weather",
    "soil_moisture",
    "vegetation_index",
    "temperature",
    "rainfall",
    "satellite",
    "other",
}


class ObservationBase(BaseSchema):
    """Base fields for Observation."""

    observation_type: str = Field(..., max_length=100)
    source: str = Field(..., min_length=1, max_length=100)
    observed_at: datetime
    value: Optional[float] = None
    unit: Optional[str] = Field(None, max_length=50)
    metadata_json: Dict[str, Any] = Field(default_factory=dict, alias="metadata")

    @field_validator("observation_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in VALID_OBSERVATION_TYPES:
            raise ValueError(
                f"Invalid observation_type '{v}'. Supported: {sorted(list(VALID_OBSERVATION_TYPES))}"
            )
        return clean


class ObservationCreate(ObservationBase):
    """Payload for creating a new Observation."""

    farm_id: Optional[uuid.UUID] = None
    zone_id: Optional[uuid.UUID] = None


class ObservationResponse(ObservationBase):
    """Response representation of an Observation record."""

    id: uuid.UUID
    farm_id: uuid.UUID
    zone_id: Optional[uuid.UUID] = None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def resolve_orm(cls, data: Any) -> Any:
        if hasattr(data, "metadata_json"):
            return {
                "id": data.id,
                "farm_id": data.farm_id,
                "zone_id": getattr(data, "zone_id", None),
                "observation_type": data.observation_type,
                "source": data.source,
                "observed_at": data.observed_at,
                "value": getattr(data, "value", None),
                "unit": getattr(data, "unit", None),
                "metadata": data.metadata_json or {},
                "created_at": getattr(data, "created_at", None),
            }
        return data
