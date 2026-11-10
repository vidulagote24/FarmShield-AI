"""Normalizer for soil telemetry, laboratory tests, and soil moisture features."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid

from app.schemas.observation import ObservationCreate
from app.intelligence.features.soil import SoilFeatures
from app.intelligence.types import (
    DataQualityStatus,
    ProvenanceType,
    SoilTextureClass,
)


class SoilNormalizationError(ValueError):
    """Raised when soil payload violates physical or agronomic bounds."""
    pass


def normalize_sensor_soil_reading(
    payload: Dict[str, Any],
    farm_id: Optional[uuid.UUID] = None,
    zone_id: Optional[uuid.UUID] = None,
    field_capacity_m3_m3: float = 0.35,
    wilting_point_m3_m3: float = 0.18,
    soil_texture: SoilTextureClass = SoilTextureClass.CLAY_LOAM,
) -> Tuple[List[ObservationCreate], SoilFeatures]:
    """Normalize in-situ soil moisture probe reading into ObservationCreate and SoilFeatures."""
    sensor_id = payload.get("sensor_id", "SENSOR_UNKNOWN")
    vwc = float(payload.get("volumetric_water_content_m3_m3", 0.0))
    d_min = float(payload.get("depth_min_cm", 0.0))
    d_max = float(payload.get("depth_max_cm", 30.0))

    if not (0.0 <= vwc <= 1.0):
        raise SoilNormalizationError(f"Volumetric water content {vwc} m³/m³ is outside physical bounds [0, 1].")
    if d_min < 0.0 or d_max <= d_min:
        raise SoilNormalizationError(f"Invalid sensor depth range: [{d_min}, {d_max}] cm.")

    dt_str = payload.get("observed_at")
    if dt_str:
        if dt_str.endswith("Z"):
            observed_at = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        elif "+" in dt_str or "-" in dt_str[10:]:
            observed_at = datetime.fromisoformat(dt_str)
        else:
            observed_at = datetime.fromisoformat(dt_str).replace(tzinfo=timezone.utc)
    else:
        observed_at = datetime.now(timezone.utc)

    retrieved_at = datetime.now(timezone.utc)
    awc = max(0.0, round(field_capacity_m3_m3 - wilting_point_m3_m3, 4))

    soil_features = SoilFeatures(
        source_provider=f"In-situ probe ({sensor_id})",
        provenance_type=ProvenanceType.SENSOR_MEASURED,
        observed_at=observed_at,
        retrieved_at=retrieved_at,
        depth_min_cm=d_min,
        depth_max_cm=d_max,
        soil_moisture_m3_m3=round(vwc, 4),
        field_capacity_m3_m3=round(field_capacity_m3_m3, 4),
        wilting_point_m3_m3=round(wilting_point_m3_m3, 4),
        available_water_capacity_m3_m3=awc,
        soil_texture=soil_texture,
        quality_status=DataQualityStatus.GOOD,
    )

    observations = [
        ObservationCreate(
            farm_id=farm_id,
            zone_id=zone_id,
            observation_type="soil_moisture",
            source=f"In-situ sensor ({sensor_id})",
            observed_at=observed_at,
            value=round(vwc, 4),
            unit="m³/m³",
            metadata={
                "depth_min_cm": d_min,
                "depth_max_cm": d_max,
                "field_capacity_m3_m3": field_capacity_m3_m3,
                "wilting_point_m3_m3": wilting_point_m3_m3,
                "battery_pct": payload.get("battery_pct"),
                "soil_temperature_c": payload.get("soil_temperature_c"),
                "provenance": "sensor_measured",
            },
        )
    ]

    return observations, soil_features


def normalize_open_meteo_soil_moisture(
    raw_weather_payload: Dict[str, Any],
    farm_id: Optional[uuid.UUID] = None,
    zone_id: Optional[uuid.UUID] = None,
    field_capacity_m3_m3: float = 0.35,
    wilting_point_m3_m3: float = 0.18,
    soil_texture: SoilTextureClass = SoilTextureClass.CLAY_LOAM,
) -> Tuple[List[ObservationCreate], Optional[SoilFeatures]]:
    """Extract and normalize Open-Meteo modelled gridded soil moisture (0-7cm) as PROVIDER_MODELLED."""
    if not isinstance(raw_weather_payload, dict) or "hourly" not in raw_weather_payload:
        return [], None

    hourly = raw_weather_payload["hourly"]
    sm_0_7 = hourly.get("soil_moisture_0_to_7cm", [])
    times = hourly.get("time", [])

    if not sm_0_7 or not times:
        return [], None

    latest_val = None
    latest_time_str = None
    for val, t_str in zip(reversed(sm_0_7), reversed(times)):
        if val is not None:
            latest_val = float(val)
            latest_time_str = t_str
            break

    if latest_val is None or latest_time_str is None:
        return [], None

    if latest_time_str.endswith("Z"):
        observed_at = datetime.fromisoformat(latest_time_str.replace("Z", "+00:00"))
    elif "+" in latest_time_str or "-" in latest_time_str[10:]:
        observed_at = datetime.fromisoformat(latest_time_str)
    else:
        observed_at = datetime.fromisoformat(latest_time_str).replace(tzinfo=timezone.utc)

    awc = max(0.0, round(field_capacity_m3_m3 - wilting_point_m3_m3, 4))

    soil_features = SoilFeatures(
        source_provider="Open-Meteo Soil Model",
        provenance_type=ProvenanceType.PROVIDER_MODELLED,
        observed_at=observed_at,
        retrieved_at=datetime.now(timezone.utc),
        depth_min_cm=0.0,
        depth_max_cm=7.0,
        soil_moisture_m3_m3=round(latest_val, 4),
        field_capacity_m3_m3=round(field_capacity_m3_m3, 4),
        wilting_point_m3_m3=round(wilting_point_m3_m3, 4),
        available_water_capacity_m3_m3=awc,
        soil_texture=soil_texture,
        quality_status=DataQualityStatus.GOOD,
    )

    observations = [
        ObservationCreate(
            farm_id=farm_id,
            zone_id=zone_id,
            observation_type="soil_moisture",
            source="Open-Meteo Modelled Soil Layer",
            observed_at=observed_at,
            value=round(latest_val, 4),
            unit="m³/m³",
            metadata={
                "depth_min_cm": 0.0,
                "depth_max_cm": 7.0,
                "provenance": "provider_modelled",
                "note": "Modelled reanalysis soil layer, NOT an in-situ field sensor measurement",
            },
        )
    ]

    return observations, soil_features
