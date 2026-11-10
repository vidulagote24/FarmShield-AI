"""Tests for application package namespace and import compatibility bridge."""

from datetime import datetime, timezone
import pytest
from pydantic import BaseModel


def test_import_bridge_module_and_class_identity():
    """Verify both 'app' and 'backend.app' resolve to identical module and class objects."""
    import app.intelligence.types as t_app
    import backend.app.intelligence.types as t_backend

    assert t_app is t_backend, "Module objects must be identical in sys.modules."
    assert t_app.DataQualityStatus is t_backend.DataQualityStatus, (
        "Enum classes imported from app and backend.app must be identical objects."
    )
    assert t_app.ProvenanceType is t_backend.ProvenanceType, (
        "ProvenanceType imported from app and backend.app must be identical objects."
    )


def test_cross_imported_pydantic_validation():
    """Verify Pydantic models accept classes imported across app and backend.app namespaces."""
    import app.intelligence.features.weather as w_app
    import backend.app.intelligence.features.weather as w_backend
    from app.intelligence.features.feature_builder import MultimodalZoneFeatureSet
    from app.intelligence.types import DataQualityStatus, ProvenanceType

    assert w_app.WeatherFeatures is w_backend.WeatherFeatures

    now = datetime.now(timezone.utc)
    weather = w_backend.WeatherFeatures(
        source_provider="Open-Meteo Forecast API",
        provenance_type=ProvenanceType.PROVIDER_MODELLED,
        observed_at=now,
        window_start=now,
        window_end=now,
        temperature_mean_c=25.0,
        relative_humidity_mean_pct=60.0,
        wind_speed_mean_m_s=3.0,
        quality_status=DataQualityStatus.GOOD,
    )

    # Construct MultimodalZoneFeatureSet from app namespace using backend-imported WeatherFeatures
    feature_set = MultimodalZoneFeatureSet(
        zone_id="zone-test-1",
        as_of_time=now,
        overall_quality=DataQualityStatus.GOOD,
        weather=weather,
    )
    assert feature_set.weather is not None
    assert feature_set.weather.temperature_mean_c == 25.0


def test_fastapi_app_startup_and_metadata():
    """Verify FastAPI application instance initializes cleanly with correct title and configuration."""
    from app.main import app

    assert app.title == "FarmShield AI Backend"
    assert app.version == "1.0.0"

    openapi_paths = app.openapi()["paths"]
    assert "/api/v1/ingestion/status" in openapi_paths
    assert "/api/v1/ingestion/weather" in openapi_paths
    assert "/api/v1/ingestion/satellite" in openapi_paths
    assert "/api/v1/ingestion/soil" in openapi_paths
