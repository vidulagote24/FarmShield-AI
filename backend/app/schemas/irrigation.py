"""Pydantic schemas for IrrigationEvent records."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import Field
from app.schemas.common import BaseSchema


class IrrigationEventBase(BaseSchema):
    """Base fields for IrrigationEvent."""

    irrigation_date: datetime
    water_quantity: float = Field(..., gt=0, description="Amount of water applied (positive value)")
    water_unit: str = Field("liters", min_length=1, max_length=50)
    irrigation_method: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class IrrigationEventCreate(IrrigationEventBase):
    """Payload for creating a new IrrigationEvent."""

    farm_id: Optional[uuid.UUID] = None
    zone_id: Optional[uuid.UUID] = None


class IrrigationEventUpdate(BaseSchema):
    """Payload for updating an IrrigationEvent."""

    irrigation_date: Optional[datetime] = None
    water_quantity: Optional[float] = Field(None, gt=0)
    water_unit: Optional[str] = Field(None, min_length=1, max_length=50)
    irrigation_method: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    zone_id: Optional[uuid.UUID] = None


class IrrigationEventResponse(IrrigationEventBase):
    """Response representation of an IrrigationEvent."""

    id: uuid.UUID
    farm_id: uuid.UUID
    zone_id: Optional[uuid.UUID] = None
    created_at: datetime
