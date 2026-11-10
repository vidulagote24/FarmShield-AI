"""Normalizer for Sentinel-2 satellite observations and vegetation feature generation."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid

from app.schemas.observation import ObservationCreate
from backend.app.intelligence.features.vegetation import ZoneVegetationFeatures
from backend.app.intelligence.types import (
    DataQualityStatus,
    ProvenanceType,
    ZoneRasterStats,
)


class SatelliteNormalizationError(ValueError):
    """Raised when satellite payload fails structural or agronomic validation."""
    pass


def normalize_sentinel2_vegetation(
    stac_item: Dict[str, Any],
    ndvi_stats: Optional[ZoneRasterStats] = None,
    ndmi_stats: Optional[ZoneRasterStats] = None,
    farm_id: Optional[uuid.UUID] = None,
    zone_id: Optional[uuid.UUID] = None,
    total_pixels_in_geometry: int = 100,
    valid_pixels_count: int = 95,
) -> Tuple[List[ObservationCreate], ZoneVegetationFeatures]:
    """Normalize Sentinel-2 STAC metadata and zone raster stats into ObservationCreate and ZoneVegetationFeatures.

    Args:
        stac_item: STAC GeoJSON feature representing Sentinel-2 scene.
        ndvi_stats: Pre-aggregated zone NDVI statistics.
        ndmi_stats: Pre-aggregated zone NDMI statistics.
        farm_id: Optional Farm UUID.
        zone_id: Optional Zone UUID.
        total_pixels_in_geometry: Total pixels inside zone polygon.
        valid_pixels_count: Count of clear, unmasked vegetation/soil pixels.

    Returns:
        Tuple of:
          1. List of ObservationCreate models.
          2. ZoneVegetationFeatures ready for intelligence engine.
    """
    if not isinstance(stac_item, dict):
        raise SatelliteNormalizationError("stac_item must be a valid dictionary.")

    scene_id = stac_item.get("id", "S2_UNKNOWN_SCENE")
    props = stac_item.get("properties", {})

    dt_str = props.get("datetime")
    if not dt_str:
        raise SatelliteNormalizationError(f"STAC item '{scene_id}' is missing properties.datetime.")

    if dt_str.endswith("Z"):
        observed_at = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    elif "+" in dt_str or "-" in dt_str[10:]:
        observed_at = datetime.fromisoformat(dt_str)
    else:
        observed_at = datetime.fromisoformat(dt_str).replace(tzinfo=timezone.utc)

    cloud_cover = float(props.get("eo:cloud_cover", 0.0))
    retrieved_at = datetime.now(timezone.utc)

    # Determine data quality
    valid_fraction = valid_pixels_count / max(1, total_pixels_in_geometry)
    cloud_frac = cloud_cover / 100.0 if cloud_cover else 0.0
    if cloud_cover > 50.0:
        quality_status = DataQualityStatus.CLOUD_CONTAMINATED
    elif valid_fraction < 0.5:
        quality_status = DataQualityStatus.PARTIAL
    else:
        quality_status = DataQualityStatus.GOOD

    vegetation_features = ZoneVegetationFeatures(
        zone_id=str(zone_id) if zone_id else None,
        scene_id=scene_id,
        source_provider="Copernicus Sentinel-2 L2A",
        observed_at=observed_at,
        retrieved_at=retrieved_at,
        provenance_type=ProvenanceType.SATELLITE_DERIVED,
        total_pixels_in_geometry=total_pixels_in_geometry,
        valid_vegetation_pixel_count=valid_pixels_count,
        valid_observation_fraction=round(valid_fraction, 4),
        cloud_fraction=round(cloud_frac, 4),
        ndvi_mean=ndvi_stats.mean if ndvi_stats else None,
        ndvi_median=ndvi_stats.median if ndvi_stats else None,
        ndvi_min=ndvi_stats.min if ndvi_stats else None,
        ndvi_max=ndvi_stats.max if ndvi_stats else None,
        ndvi_std=ndvi_stats.std if ndvi_stats else None,
        ndmi_mean=ndmi_stats.mean if ndmi_stats else None,
        ndmi_median=ndmi_stats.median if ndmi_stats else None,
        ndmi_std=ndmi_stats.std if ndmi_stats else None,
        quality_status=quality_status,
    )

    observations: List[ObservationCreate] = []

    # Store NDVI observation if computed
    if ndvi_stats is not None and ndvi_stats.mean is not None:
        observations.append(
            ObservationCreate(
                farm_id=farm_id,
                zone_id=zone_id,
                observation_type="vegetation_index",
                source="Copernicus Sentinel-2 L2A",
                observed_at=observed_at,
                value=round(ndvi_stats.mean, 4),
                unit="index",
                metadata={
                    "scene_id": scene_id,
                    "index_name": "NDVI",
                    "min": ndvi_stats.min,
                    "max": ndvi_stats.max,
                    "std": ndvi_stats.std,
                    "cloud_cover_pct": cloud_cover,
                    "valid_fraction": valid_fraction,
                },
            )
        )

    # Store NDMI observation if computed
    if ndmi_stats is not None and ndmi_stats.mean is not None:
        observations.append(
            ObservationCreate(
                farm_id=farm_id,
                zone_id=zone_id,
                observation_type="vegetation_index",
                source="Copernicus Sentinel-2 L2A",
                observed_at=observed_at,
                value=round(ndmi_stats.mean, 4),
                unit="index",
                metadata={
                    "scene_id": scene_id,
                    "index_name": "NDMI",
                    "min": ndmi_stats.min,
                    "max": ndmi_stats.max,
                    "std": ndmi_stats.std,
                    "cloud_cover_pct": cloud_cover,
                },
            )
        )

    # Store general satellite scene record
    observations.append(
        ObservationCreate(
            farm_id=farm_id,
            zone_id=zone_id,
            observation_type="satellite",
            source="Copernicus Sentinel-2 L2A",
            observed_at=observed_at,
            value=round(cloud_cover, 2),
            unit="pct_cloud_cover",
            metadata={
                "scene_id": scene_id,
                "platform": props.get("platform", "Sentinel-2"),
                "instrument": "MSI",
                "processing_level": "Level-2A",
                "valid_pixels": valid_pixels_count,
                "total_pixels": total_pixels_in_geometry,
            },
        )
    )

    return observations, vegetation_features
