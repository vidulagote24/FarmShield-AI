"""Unit and integration tests for soil telemetry and moisture ingestion."""

from datetime import datetime, timezone
import pytest

from app.ingestion.normalizers.soil_normalizer import (
    SoilNormalizationError,
    normalize_open_meteo_soil_moisture,
    normalize_sensor_soil_reading,
)
from app.ingestion.providers.soil_provider import SoilMeasurementProvider
from app.intelligence.types import DataQualityStatus, ProvenanceType, SoilTextureClass


def test_sensor_soil_reading_normalization():
    """Verify in-situ sensor telemetry normalization."""
    provider = SoilMeasurementProvider()
    res = provider.ingest_sensor_reading(
        sensor_id="PROBE-ZONE-A",
        depth_min_cm=0.0,
        depth_max_cm=30.0,
        volumetric_water_content=0.28,
        observed_at=datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc),
        battery_pct=95.0,
        soil_temp_c=24.5,
    )

    obs_list, soil_feats = normalize_sensor_soil_reading(
        payload=res.payload,
        field_capacity_m3_m3=0.34,
        wilting_point_m3_m3=0.17,
        soil_texture=SoilTextureClass.CLAY_LOAM,
    )

    assert soil_feats.source_provider == "In-situ probe (PROBE-ZONE-A)"
    assert soil_feats.provenance_type == ProvenanceType.SENSOR_MEASURED
    assert soil_feats.soil_moisture_m3_m3 == 0.28
    assert soil_feats.depth_min_cm == 0.0
    assert soil_feats.depth_max_cm == 30.0
    assert soil_feats.field_capacity_m3_m3 == 0.34
    assert soil_feats.wilting_point_m3_m3 == 0.17
    assert soil_feats.available_water_capacity_m3_m3 == round(0.34 - 0.17, 4)
    assert soil_feats.soil_texture == SoilTextureClass.CLAY_LOAM
    assert soil_feats.quality_status == DataQualityStatus.GOOD

    assert len(obs_list) == 1
    assert obs_list[0].observation_type == "soil_moisture"
    assert obs_list[0].value == 0.28
    assert obs_list[0].unit == "m³/m³"
    assert obs_list[0].metadata_json["provenance"] == "sensor_measured"


def test_sensor_soil_reading_invalid_bounds_rejected():
    """Verify physical impossibility bounds are rejected."""
    with pytest.raises(SoilNormalizationError):
        normalize_sensor_soil_reading({
            "volumetric_water_content_m3_m3": 1.45,  # Impossible moisture > 1.0
            "depth_min_cm": 0.0,
            "depth_max_cm": 30.0,
        })

    with pytest.raises(SoilNormalizationError):
        normalize_sensor_soil_reading({
            "volumetric_water_content_m3_m3": 0.25,
            "depth_min_cm": 30.0,
            "depth_max_cm": 10.0,  # Inverted depth
        })


def test_modelled_soil_moisture_from_weather():
    """Verify modelled soil moisture is classified as PROVIDER_MODELLED, not sensor."""
    weather_payload = {
        "hourly": {
            "time": ["2026-11-10T00:00", "2026-11-10T01:00"],
            "soil_moisture_0_to_7cm": [0.295, 0.292],
        }
    }
    obs_list, soil_feats = normalize_open_meteo_soil_moisture(weather_payload)
    assert soil_feats is not None
    assert soil_feats.provenance_type == ProvenanceType.PROVIDER_MODELLED
    assert soil_feats.soil_moisture_m3_m3 == 0.292
    assert soil_feats.depth_min_cm == 0.0
    assert soil_feats.depth_max_cm == 7.0

    assert len(obs_list) == 1
    assert obs_list[0].metadata_json["provenance"] == "provider_modelled"
