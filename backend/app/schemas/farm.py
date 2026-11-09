"""Pydantic schemas for Farm, FarmBoundary, and FarmZone entities with GeoJSON serialization."""

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import Field, field_serializer, field_validator, model_validator
from app.core.spatial import (
    geometry_to_geojson_dict,
    validate_geojson_multipolygon,
    validate_geojson_polygon,
)
from app.schemas.common import BaseSchema


class FarmBase(BaseSchema):
    """Base fields for Farm entity."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    location_name: Optional[str] = Field(None, max_length=255)
    crop_type: str = Field(..., min_length=1, max_length=100)
    crop_variety: Optional[str] = Field(None, max_length=100)
    sowing_date: Optional[date] = None


class FarmCreate(FarmBase):
    """Payload for creating a new Farm including its GeoJSON boundary."""

    boundary: Dict[str, Any] = Field(
        ...,
        description="GeoJSON Polygon or MultiPolygon geometry dictionary (WGS84 / SRID 4326).",
    )

    @field_validator("boundary")
    @classmethod
    def validate_boundary_geometry(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate topological validity and coordinate bounds."""
        validate_geojson_multipolygon(v)
        return v


class FarmUpdate(BaseSchema):
    """Payload for updating farm descriptive metadata."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    location_name: Optional[str] = Field(None, max_length=255)
    crop_type: Optional[str] = Field(None, min_length=1, max_length=100)
    crop_variety: Optional[str] = Field(None, max_length=100)
    sowing_date: Optional[date] = None


class FarmBoundaryUpdate(BaseSchema):
    """Payload for updating farm spatial boundary."""

    boundary: Dict[str, Any] = Field(
        ...,
        description="GeoJSON Polygon or MultiPolygon geometry dictionary.",
    )

    @field_validator("boundary")
    @classmethod
    def validate_boundary_geometry(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        validate_geojson_multipolygon(v)
        return v


class FarmBoundaryResponse(BaseSchema):
    """Spatial boundary representation of a Farm."""

    id: uuid.UUID
    name: str
    boundary: Dict[str, Any]
    area_hectares: float

    @field_validator("boundary", mode="before")
    @classmethod
    def serialize_geometry(cls, v: Any) -> Dict[str, Any]:
        return geometry_to_geojson_dict(v)


class FarmResponse(FarmBase):
    """Complete response representation of a Farm."""

    id: uuid.UUID
    owner_id: uuid.UUID
    boundary: Dict[str, Any]
    area_hectares: float
    created_at: datetime
    updated_at: datetime

    @field_validator("boundary", mode="before")
    @classmethod
    def serialize_geometry(cls, v: Any) -> Dict[str, Any]:
        return geometry_to_geojson_dict(v)


# FarmZone Schemas
class FarmZoneBase(BaseSchema):
    """Base fields for FarmZone entity."""

    zone_name: str = Field(..., min_length=1, max_length=255)
    zone_code: str = Field(..., min_length=1, max_length=50)
    metadata_json: Dict[str, Any] = Field(
        default_factory=dict,
        alias="metadata",
        description="Custom operational zone metadata (soil sensor IDs, topography notes, etc.)",
    )


class FarmZoneCreate(FarmZoneBase):
    """Payload for creating a new FarmZone."""

    boundary: Dict[str, Any] = Field(
        ...,
        description="GeoJSON Polygon geometry dictionary (WGS84 / SRID 4326).",
    )

    @field_validator("boundary")
    @classmethod
    def validate_zone_geometry(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        validate_geojson_polygon(v)
        return v


class FarmZoneUpdate(BaseSchema):
    """Payload for updating a FarmZone."""

    zone_name: Optional[str] = Field(None, min_length=1, max_length=255)
    zone_code: Optional[str] = Field(None, min_length=1, max_length=50)
    boundary: Optional[Dict[str, Any]] = None
    metadata_json: Optional[Dict[str, Any]] = Field(None, alias="metadata")

    @field_validator("boundary")
    @classmethod
    def validate_zone_geometry(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if v is not None:
            validate_geojson_polygon(v)
        return v


class FarmZoneResponse(FarmZoneBase):
    """Response representation of a FarmZone."""

    id: uuid.UUID
    farm_id: uuid.UUID
    boundary: Dict[str, Any]
    area_hectares: float
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def resolve_orm(cls, data: Any) -> Any:
        if hasattr(data, "metadata_json"):
            return {
                "id": data.id,
                "farm_id": data.farm_id,
                "zone_name": data.zone_name,
                "zone_code": data.zone_code,
                "boundary": geometry_to_geojson_dict(data.boundary),
                "area_hectares": data.area_hectares,
                "metadata": data.metadata_json or {},
                "created_at": getattr(data, "created_at", None),
                "updated_at": getattr(data, "updated_at", None),
            }
        return data

    @field_validator("boundary", mode="before")
    @classmethod
    def serialize_geometry(cls, v: Any) -> Dict[str, Any]:
        return geometry_to_geojson_dict(v)
