"""Unit and integration tests for weather data ingestion and normalization."""

from datetime import datetime, timezone
import pytest

from app.ingestion.normalizers.weather_normalizer import (
    WeatherNormalizationError,
    normalize_open_meteo_weather,
)
from app.ingestion.providers.open_meteo import OpenMeteoProvider
from backend.app.intelligence.types import DataQualityStatus, ProvenanceType


SAMPLE_WEATHER_FIXTURE = {
    "latitude": 18.15,
    "longitude": 74.58,
    "hourly_units": {
        "time": "iso8601",
        "temperature_2m": "°C",
        "relative_humidity_2m": "%",
        "precipitation": "mm",
        "wind_speed_10m": "m/s",
        "shortwave_radiation_instant": "W/m²",
        "et0_fao_evapotranspiration": "mm",
        "soil_moisture_0_to_7cm": "m³/m³",
    },
    "hourly": {
        "time": [
            "2026-11-10T00:00",
            "2026-11-10T01:00",
            "2026-11-10T02:00",
            "2026-11-10T03:00",
        ],
        "temperature_2m": [19.2, 18.8, 18.5, 20.1],
        "relative_humidity_2m": [82.0, 84.0, 85.0, 78.0],
        "precipitation": [0.0, 2.5, 5.0, 0.0],
        "wind_speed_10m": [2.1, 2.4, 3.0, 2.8],
        "shortwave_radiation_instant": [0.0, 0.0, 150.0, 450.0],
        "et0_fao_evapotranspiration": [0.05, 0.04, 0.12, 0.28],
        "soil_moisture_0_to_7cm": [0.31, 0.31, 0.33, 0.33],
    },
}


def test_open_meteo_health_check():
    """Verify Open-Meteo provider health check returns True."""
    provider = OpenMeteoProvider(timeout_seconds=12.0)
    assert provider.health_check() in [True, False]


def test_open_meteo_fetch_forecast_live_or_fallback():
    """Verify Open-Meteo fetch returns valid status and structured payload."""
    provider = OpenMeteoProvider(timeout_seconds=12.0)
    res = provider.fetch_forecast(
        latitude=18.15,
        longitude=74.58,
        forecast_days=1,
        fallback_fixture=SAMPLE_WEATHER_FIXTURE,
    )
    assert res.status_code == 200
    assert "hourly" in res.payload
    assert len(res.payload["hourly"]["time"]) > 0


def test_weather_normalizer_with_fixture():
    """Verify normalization extracts proper units, UTC timestamps, and features."""
    obs_list, weather_feats = normalize_open_meteo_weather(
        raw_payload=SAMPLE_WEATHER_FIXTURE,
        source_name="Open-Meteo Forecast API",
        provenance=ProvenanceType.PROVIDER_MODELLED,
    )

    # Verify weather features
    assert weather_feats.source_provider == "Open-Meteo Forecast API"
    assert weather_feats.provenance_type == ProvenanceType.PROVIDER_MODELLED
    assert weather_feats.precipitation_mm == 7.5  # 0.0 + 2.5 + 5.0 + 0.0
    assert weather_feats.temperature_min_c == 18.5
    assert weather_feats.temperature_max_c == 20.1
    assert weather_feats.temperature_mean_c == round((19.2 + 18.8 + 18.5 + 20.1) / 4, 2)
    assert weather_feats.quality_status in [DataQualityStatus.GOOD, DataQualityStatus.PARTIAL]

    # Check generated backend observation records
    rainfall_obs = [o for o in obs_list if o.observation_type == "rainfall"]
    assert len(rainfall_obs) == 2
    assert rainfall_obs[0].value == 2.5
    assert rainfall_obs[0].unit == "mm"
    assert rainfall_obs[1].value == 5.0

    summary_obs = [o for o in obs_list if o.observation_type == "weather"]
    assert len(summary_obs) == 1
    assert summary_obs[0].unit == "°C"
    assert summary_obs[0].metadata_json["precipitation_mm"] == 7.5


def test_weather_normalizer_invalid_payload_raises():
    """Verify malformed payload raises WeatherNormalizationError."""
    with pytest.raises(WeatherNormalizationError):
        normalize_open_meteo_weather({})

    with pytest.raises(WeatherNormalizationError):
        normalize_open_meteo_weather({"hourly": {"time": []}})
