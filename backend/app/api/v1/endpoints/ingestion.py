"""API v1 Endpoints for Data Ingestion pipelines."""

from datetime import datetime, timezone
import math
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2.shape import to_shape
import numpy as np
from pydantic import BaseModel, Field
import pyproj
import shapely
import shapely.geometry
from sqlalchemy.orm import Session

from app.api.deps import check_farm_ownership, get_current_active_user, get_db
from app.ingestion.pipelines.pipeline import IngestionPipeline
from app.models.farm import Farm, FarmZone
from app.models.user import User

router = APIRouter(prefix="/ingestion", tags=["Data Ingestion"])
pipeline = IngestionPipeline()

# Cache for /status endpoint to throttle external network calls and protect provider quotas.
# Architectural & Concurrency Strategy:
# 1. Thread Synchronization: _STATUS_CACHE_LOCK with double-checked locking guarantees that
#    concurrent requests during cache expiry do not trigger redundant external HTTP probes.
# 2. Scope & Boundaries: This in-memory cache is local to the operating process/worker.
#    In multi-worker deployments (e.g. uvicorn --workers > 1), each worker maintains an independent
#    60s cache window. For a distributed cluster, a Redis-backed cache would be required.
#    Since no Redis broker is configured in FarmShield MVP, this thread-safe in-memory cache provides
#    immediate rate-limit protection with zero infrastructure dependencies.
_STATUS_CACHE: Dict[str, Any] = {"timestamp": 0.0, "data": None}
_CACHE_TTL_SECONDS = 60.0
_STATUS_CACHE_LOCK = threading.Lock()


def _reproject_geometry(
    geom: shapely.geometry.base.BaseGeometry,
    from_srid: int,
    to_srid: int = 4326,
) -> shapely.geometry.base.BaseGeometry:
    """Reproject a Shapely geometry from from_srid to to_srid (default WGS84 4326)."""
    if from_srid == to_srid:
        return geom
    try:
        transformer = pyproj.Transformer.from_crs(f"EPSG:{from_srid}", f"EPSG:{to_srid}", always_xy=True)
    except Exception as exc:
        raise ValueError(f"Invalid or unsupported CRS SRID {from_srid}: {exc}") from exc

    def _project(coords: np.ndarray) -> np.ndarray:
        x, y = transformer.transform(coords[:, 0], coords[:, 1])
        return np.column_stack([x, y])

    return shapely.transform(geom, _project)


def validate_farm_and_zone_access(
    db: Session,
    current_user: User,
    farm_id: Optional[uuid.UUID],
    zone_id: Optional[uuid.UUID],
    require_farm: bool = False,
) -> Tuple[Optional[Farm], Optional[FarmZone]]:
    """Enforce the strict 7-step farm and zone ownership validation sequence.

    Sequence:
    1. Authenticate user (enforced upstream via get_current_active_user).
    2. Retrieve farm if farm_id is provided or required.
    3. Verify farm exists (404 Not Found if missing).
    4. Verify user ownership/access using check_farm_ownership (403 Forbidden if unauthorized).
    5. Retrieve zone if supplied (404 Not Found if missing).
    6. Verify zone belongs to farm (400 Bad Request if zone does not belong to farm).
       If zone supplied without farm_id, parent farm is resolved and verified against user ownership.
    7. Reject invalid combinations before calling external providers or persisting observations.

    Args:
        db: Active database session.
        current_user: Currently authenticated active user.
        farm_id: Optional target Farm UUID.
        zone_id: Optional target FarmZone UUID.
        require_farm: If True, farm_id must be provided (raises 400 Bad Request if absent).

    Returns:
        Tuple of (Farm or None, FarmZone or None).
    """
    farm: Optional[Farm] = None
    zone: Optional[FarmZone] = None

    if require_farm and not farm_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="farm_id is required for this operation.",
        )

    if farm_id:
        farm = db.query(Farm).filter(Farm.id == farm_id).first()
        if not farm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Farm '{farm_id}' was not found.",
            )
        check_farm_ownership(farm, current_user)

    if zone_id:
        zone = db.query(FarmZone).filter(FarmZone.id == zone_id).first()
        if not zone:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone '{zone_id}' was not found.",
            )

        if farm:
            if zone.farm_id != farm.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Zone '{zone_id}' does not belong to farm '{farm.id}'.",
                )
        else:
            # Zone provided without farm_id: retrieve parent farm and verify ownership without leaking metadata
            farm = db.query(Farm).filter(Farm.id == zone.farm_id).first()
            if not farm:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent farm for the specified zone was not found.",
                )
            check_farm_ownership(farm, current_user)

    return farm, zone


def validate_satellite_bbox_within_farm(
    bbox: List[float],
    farm: Farm,
) -> None:
    """Validate bounding box coordinate ranges, ordering, and containment within farm boundary.

    Checks:
    - Bbox coordinates ordering: min_lon < max_lon and min_lat < max_lat.
    - Physical coordinate limits: -180 <= lon <= 180 and -90 <= lat <= 90.
    - Finite coordinate values (rejects NaN and +/-Infinity).
    - Inspection and reprojection of farm boundary CRS (WGS84 EPSG:4326 canonical).
    - Complete containment within the farm MultiPolygon boundary (no silent clipping).
    - Rejects out-of-bound or partially outside requests with 400 Bad Request.

    Args:
        bbox: [min_lon, min_lat, max_lon, max_lat]
        farm: Farm model instance with PostGIS boundary.
    """
    if len(bbox) != 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bounding box must contain exactly 4 coordinates: [min_lon, min_lat, max_lon, max_lat].",
        )

    # 1. Finite coordinate check
    for coord in bbox:
        if not isinstance(coord, (int, float)) or not math.isfinite(coord):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bounding box coordinates must be finite real numbers; received {coord}.",
            )

    min_lon, min_lat, max_lon, max_lat = bbox

    # 2. Physical coordinate limits
    if not (-180.0 <= min_lon <= 180.0 and -180.0 <= max_lon <= 180.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bounding box longitude out of valid range [-180, 180]: min_lon={min_lon}, max_lon={max_lon}.",
        )
    if not (-90.0 <= min_lat <= 90.0 and -90.0 <= max_lat <= 90.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bounding box latitude out of valid range [-90, 90]: min_lat={min_lat}, max_lat={max_lat}.",
        )

    # 3. Coordinate ordering: min must be strictly less than max
    if min_lon >= max_lon:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid bounding box coordinate ordering: min_lon ({min_lon}) must be strictly less than max_lon ({max_lon}).",
        )
    if min_lat >= max_lat:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid bounding box coordinate ordering: min_lat ({min_lat}) must be strictly less than max_lat ({max_lat}).",
        )

    # 4. SRID Inspection & Geometry Decoding
    srid = getattr(farm.boundary, "srid", 4326)
    if srid is None or srid <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Farm boundary has missing or invalid SRID ({srid}).",
        )

    try:
        farm_shape = to_shape(farm.boundary)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to decode farm spatial boundary: {exc}",
        )

    if not farm_shape.is_valid:
        farm_shape = farm_shape.buffer(0)
        if not farm_shape.is_valid or farm_shape.is_empty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Farm boundary geometry is topologically invalid.",
            )

    # 5. Transform farm geometry to canonical WGS84 (EPSG:4326) if stored in a different projection
    if srid != 4326:
        try:
            farm_shape = _reproject_geometry(farm_shape, from_srid=srid, to_srid=4326)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported spatial reference system (SRID {srid}) on farm boundary: {exc}",
            )

    # 6. Containment testing (supports Polygon and MultiPolygon)
    bbox_shape = shapely.geometry.box(min_lon, min_lat, max_lon, max_lat)

    if not farm_shape.covers(bbox_shape):
        if farm_shape.intersects(bbox_shape):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Requested bounding box extends outside the farm boundary. Bounding box must be fully contained within the farm.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Requested bounding box is completely outside the farm boundary.",
            )


class WeatherIngestRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees")
    farm_id: Optional[uuid.UUID] = Field(default=None, description="Optional Farm UUID for persistence")
    zone_id: Optional[uuid.UUID] = Field(default=None, description="Optional Zone UUID for persistence")
    forecast_days: int = Field(default=3, ge=1, le=7, description="Number of forecast days")


class SatelliteIngestRequest(BaseModel):
    farm_id: uuid.UUID = Field(..., description="Target Farm UUID (required for boundary containment)")
    bbox: List[float] = Field(..., min_length=4, max_length=4, description="[min_lon, min_lat, max_lon, max_lat]")
    start_date: str = Field(..., description="Start date YYYY-MM-DD")
    end_date: str = Field(..., description="End date YYYY-MM-DD")
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
    description="Check reachability and operational status of external data ingestion providers (cached for 60s, requires authentication).",
)
def get_providers_status(
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Return health check status across all external providers with synchronized 60s cache protection.

    Architecture & Multi-Worker Concurrency Note:
    - Thread synchronization (_STATUS_CACHE_LOCK) with double-checked locking ensures that concurrent
      requests during cache expiration only trigger one external probe across threads.
    - Important: This cache is in-process memory. In a multi-worker process deployment (e.g., uvicorn with N workers),
      each worker process maintains its own independent 60-second cache. For single-worker or low-worker hackathon
      deployments, this completely eliminates redundant provider requests without adding external Redis dependencies.
      In a distributed multi-node cluster, a centralized cache (such as Redis) should be introduced.
    """
    now = time.time()
    if _STATUS_CACHE["data"] is not None and (now - _STATUS_CACHE["timestamp"]) < _CACHE_TTL_SECONDS:
        return _STATUS_CACHE["data"]

    with _STATUS_CACHE_LOCK:
        now = time.time()
        if _STATUS_CACHE["data"] is not None and (now - _STATUS_CACHE["timestamp"]) < _CACHE_TTL_SECONDS:
            return _STATUS_CACHE["data"]

        providers_status: Dict[str, Any] = {}
        all_operational = True

        for key, provider in [
            ("open_meteo", pipeline.weather_provider),
            ("sentinel2_stac", pipeline.satellite_provider),
            ("soil_adapter", pipeline.soil_provider),
        ]:
            try:
                reachable = bool(provider.health_check())
                error_msg = None
            except Exception as exc:
                reachable = False
                error_msg = str(exc)

            if not reachable:
                all_operational = False

            providers_status[key] = {
                "name": provider.provider_name,
                "reachable": reachable,
                "error": error_msg,
            }

        overall_status = "operational" if all_operational else "degraded"

        status_data = {
            "status": overall_status,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "providers": providers_status,
        }
        _STATUS_CACHE["timestamp"] = now
        _STATUS_CACHE["data"] = status_data
        return status_data


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
    """Ingest meteorological forecast for given coordinates with ownership validation."""
    farm, zone = validate_farm_and_zone_access(
        db=db,
        current_user=current_user,
        farm_id=req.farm_id,
        zone_id=req.zone_id,
        require_farm=False,
    )

    persisted, weather_features, soil_features = pipeline.ingest_weather_for_coordinates(
        latitude=req.latitude,
        longitude=req.longitude,
        farm_id=farm.id if farm else None,
        zone_id=zone.id if zone else None,
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
    """Search and ingest Sentinel-2 metadata with boundary containment validation."""
    farm, zone = validate_farm_and_zone_access(
        db=db,
        current_user=current_user,
        farm_id=req.farm_id,
        zone_id=req.zone_id,
        require_farm=True,
    )
    validate_satellite_bbox_within_farm(req.bbox, farm)

    persisted, veg_features = pipeline.ingest_satellite_for_bbox(
        bbox=req.bbox,
        start_date=req.start_date,
        end_date=req.end_date,
        farm_id=farm.id,
        zone_id=zone.id if zone else None,
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
    """Ingest soil sensor reading with ownership validation."""
    farm, zone = validate_farm_and_zone_access(
        db=db,
        current_user=current_user,
        farm_id=req.farm_id,
        zone_id=req.zone_id,
        require_farm=False,
    )

    obs_time = req.observed_at or datetime.now(timezone.utc)
    persisted, soil_features = pipeline.ingest_soil_sensor_reading(
        sensor_id=req.sensor_id,
        depth_min_cm=req.depth_min_cm,
        depth_max_cm=req.depth_max_cm,
        volumetric_water_content=req.volumetric_water_content_m3_m3,
        observed_at=obs_time,
        farm_id=farm.id if farm else None,
        zone_id=zone.id if zone else None,
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
