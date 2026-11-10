"""API v1 Endpoints for Data Ingestion pipelines."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import check_farm_ownership, get_current_active_user, get_db
from app.ingestion.pipelines.pipeline import IngestionPipeline
from app.models.farm import Farm
from app.models.user import User

router = APIRouter(prefix="/ingestion", tags=["Data Ingestion"])
pipeline = IngestionPipeline()


class WeatherIngestRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees")
    farm_id: Optional[uuid.UUID] = Field(default=None, description="Optional Farm UUID for persistence")
    zone_id: Optional[uuid.UUID] = Field(default=None, description="Optional Zone UUID for persistence")
    forecast_days: int = Field(default=3, ge=1, le=7, description="Number of forecast days")


class SatelliteIngestRequest(BaseModel):
    bbox: List[float] = Field(..., min_length=4, max_length=4, description="[min_lon, min_lat, max_lon, max_lat]")
    start_date: str = Field(..., description="Start date YYYY-MM-DD")
    end_date: str = Field(..., description="End date YYYY-MM-DD")
    farm_id: Optional[uuid.UUID] = Field(default=None, description="Optional Farm UUID for persistence")
    zone_id: Optional[uuid.UUID] = Field(default=None, description="Optional Zone UUID for persistence")
    max_cloud_cover_pct: float = Field(default=40.0, ge=0.0, le=100.0)


class SoilSensorIngestRequest(BaseModel):
    sensor_id: str = Field(..., min_length=1, max_length=100)
    depth_min_cm: float = Field(default=0.0, ge=0.0)
    depth_max_cm: float = Field(default=30.0, gt=0.0)
    volumetric_water_content_m3_m3: float = Field(..., ge=0.0, le=1.0)
    observed_at: Optional[datetime] = Field(default=None)
    farm_id: Optional[uuid.UUID] = Field(default=None)
    zone_id: Optional[uuid.UUID] = Field(default=None)


@router.get(
    "/status",
    summary="Data Ingestion Providers Status",
    description="Check reachability and operational status of external data ingestion providers.",
)
def get_providers_status() -> Dict[str, Any]:
    """Return health check status across all external providers."""
    return {
        "status": "operational",
        "providers": {
            "open_meteo": {
                "name": pipeline.weather_provider.provider_name,
                "reachable": pipeline.weather_provider.health_check(),
            },
            "sentinel2_stac": {
                "name": pipeline.satellite_provider.provider_name,
                "reachable": pipeline.satellite_provider.health_check(),
            },
            "soil_adapter": {
                "name": pipeline.soil_provider.provider_name,
                "reachable": pipeline.soil_provider.health_check(),
            },
        },
    }


@router.post(
    "/weather",
    summary="Trigger weather data ingestion",
    description="Retrieve live meteorological forecasts from Open-Meteo, normalize, and optionally persist.",
)
def ingest_weather(
    req: WeatherIngestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Ingest meteorological forecast for given coordinates."""
    if req.farm_id:
        farm = db.query(Farm).filter(Farm.id == req.farm_id).first()
        if not farm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Farm '{req.farm_id}' was not found.",
            )
        check_farm_ownership(farm, current_user)

    persisted, weather_features, soil_features = pipeline.ingest_weather_for_coordinates(
        latitude=req.latitude,
        longitude=req.longitude,
        farm_id=req.farm_id,
        zone_id=req.zone_id,
        db=db,
        forecast_days=req.forecast_days,
    )

    return {
        "status": "success",
        "persisted_observations_count": len(persisted),
        "weather_summary": {
            "source_provider": weather_features.source_provider,
            "window_start": weather_features.window_start.isoformat(),
            "window_end": weather_features.window_end.isoformat(),
            "precipitation_mm": weather_features.precipitation_mm,
            "temperature_mean_c": weather_features.temperature_mean_c,
            "relative_humidity_mean_pct": weather_features.relative_humidity_mean_pct,
            "wind_speed_mean_m_s": weather_features.wind_speed_mean_m_s,
            "quality_status": weather_features.quality_status.value,
        },
        "modelled_soil_summary": {
            "soil_moisture_m3_m3": soil_features.soil_moisture_m3_m3 if soil_features else None,
            "depth_range_cm": [soil_features.depth_min_cm, soil_features.depth_max_cm] if soil_features else None,
            "provenance": soil_features.provenance_type.value if soil_features else None,
        } if soil_features else None,
    }


@router.post(
    "/satellite",
    summary="Trigger satellite scene search and ingestion",
    description="Query Sentinel-2 Level-2A STAC items for bbox and date range, normalize metadata, and optionally persist.",
)
def ingest_satellite(
    req: SatelliteIngestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Search and ingest Sentinel-2 metadata."""
    if req.farm_id:
        farm = db.query(Farm).filter(Farm.id == req.farm_id).first()
        if not farm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Farm '{req.farm_id}' was not found.",
            )
        check_farm_ownership(farm, current_user)

    persisted, veg_features = pipeline.ingest_satellite_for_bbox(
        bbox=req.bbox,
        start_date=req.start_date,
        end_date=req.end_date,
        farm_id=req.farm_id,
        zone_id=req.zone_id,
        db=db,
        max_cloud_cover_pct=req.max_cloud_cover_pct,
    )

    return {
        "status": "success",
        "persisted_observations_count": len(persisted),
        "scene_found": veg_features is not None,
        "scene_details": {
            "scene_id": veg_features.scene_id,
            "observed_at": veg_features.observed_at.isoformat(),
            "cloud_coverage_percentage": round(veg_features.cloud_fraction * 100.0, 2) if veg_features.cloud_fraction is not None else None,
            "valid_observation_fraction": veg_features.valid_observation_fraction,
            "quality_status": veg_features.quality_status.value,
        } if veg_features else None,
    }


@router.post(
    "/soil",
    summary="Ingest in-situ soil moisture sensor reading",
    description="Ingest telemetry from physical root-zone probe and persist as observation.",
)
def ingest_soil_reading(
    req: SoilSensorIngestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Ingest soil sensor reading."""
    if req.farm_id:
        farm = db.query(Farm).filter(Farm.id == req.farm_id).first()
        if not farm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Farm '{req.farm_id}' was not found.",
            )
        check_farm_ownership(farm, current_user)

    obs_time = req.observed_at or datetime.now(timezone.utc)
    persisted, soil_features = pipeline.ingest_soil_sensor_reading(
        sensor_id=req.sensor_id,
        depth_min_cm=req.depth_min_cm,
        depth_max_cm=req.depth_max_cm,
        volumetric_water_content=req.volumetric_water_content_m3_m3,
        observed_at=obs_time,
        farm_id=req.farm_id,
        zone_id=req.zone_id,
        db=db,
    )

    return {
        "status": "success",
        "persisted_observations_count": len(persisted),
        "soil_summary": {
            "source_provider": soil_features.source_provider,
            "provenance": soil_features.provenance_type.value,
            "depth_range_cm": [soil_features.depth_min_cm, soil_features.depth_max_cm],
            "volumetric_water_content_m3_m3": soil_features.soil_moisture_m3_m3,
            "field_capacity_m3_m3": soil_features.field_capacity_m3_m3,
            "wilting_point_m3_m3": soil_features.wilting_point_m3_m3,
            "observed_at": soil_features.observed_at.isoformat(),
        },
    }
