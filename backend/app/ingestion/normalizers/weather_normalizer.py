"""Normalizer for meteorological observations and weather feature generation."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid

from app.schemas.observation import ObservationCreate
from backend.app.intelligence.features.weather import (
    HourlyWeatherReading,
    WeatherFeatures,
    aggregate_hourly_weather,
)
from backend.app.intelligence.types import (
    MeasurementHeightProvenance,
    ProvenanceType,
    SolarIrradianceType,
    WeatherWindowType,
)


class WeatherNormalizationError(ValueError):
    """Raised when weather payload fails required structural or physical validation."""
    pass


def normalize_open_meteo_weather(
    raw_payload: Dict[str, Any],
    farm_id: Optional[uuid.UUID] = None,
    zone_id: Optional[uuid.UUID] = None,
    source_name: str = "Open-Meteo Forecast API",
    provenance: ProvenanceType = ProvenanceType.PROVIDER_MODELLED,
) -> Tuple[List[ObservationCreate], WeatherFeatures]:
    """Normalize raw Open-Meteo payload into backend Observation records and WeatherFeatures."""
    if not isinstance(raw_payload, dict) or "hourly" not in raw_payload:
        raise WeatherNormalizationError("Invalid weather payload: missing 'hourly' section.")

    hourly = raw_payload["hourly"]
    times = hourly.get("time", [])
    if not times:
        raise WeatherNormalizationError("Weather payload contains empty hourly time series.")

    temperatures = hourly.get("temperature_2m", [])
    humidities = hourly.get("relative_humidity_2m", [])
    precipitations = hourly.get("precipitation", [])
    wind_speeds = hourly.get("wind_speed_10m", [])
    radiations = hourly.get("shortwave_radiation_instant", [])
    et0s = hourly.get("et0_fao_evapotranspiration", [])

    hourly_readings: List[HourlyWeatherReading] = []
    observations: List[ObservationCreate] = []

    count = len(times)
    for i in range(count):
        raw_time_str = times[i]
        if raw_time_str.endswith("Z"):
            ts = datetime.fromisoformat(raw_time_str.replace("Z", "+00:00"))
        elif "+" in raw_time_str or "-" in raw_time_str[10:]:
            ts = datetime.fromisoformat(raw_time_str)
        else:
            ts = datetime.fromisoformat(raw_time_str).replace(tzinfo=timezone.utc)

        t_val = temperatures[i] if i < len(temperatures) else None
        rh_val = humidities[i] if i < len(humidities) else None
        p_val = precipitations[i] if i < len(precipitations) else None
        w_val = wind_speeds[i] if i < len(wind_speeds) else None
        r_val = radiations[i] if i < len(radiations) else None
        et0_val = et0s[i] if i < len(et0s) else None

        p_clean = max(0.0, float(p_val)) if p_val is not None else None
        rh_clean = max(0.0, min(100.0, float(rh_val))) if rh_val is not None else None
        w_clean = max(0.0, float(w_val)) if w_val is not None else None
        r_clean = max(0.0, float(r_val)) if r_val is not None else None
        et0_clean = max(0.0, float(et0_val)) if et0_val is not None else None

        reading = HourlyWeatherReading(
            timestamp=ts,
            temperature_2m_c=float(t_val) if t_val is not None else None,
            precipitation_mm=p_clean,
            relative_humidity_2m_pct=rh_clean,
            wind_speed_10m_m_s=w_clean,
            shortwave_radiation_w_m2=r_clean,
            et0_fao_evapotranspiration_mm=et0_clean,
        )
        hourly_readings.append(reading)

        if p_clean is not None and p_clean > 0.0:
            observations.append(
                ObservationCreate(
                    farm_id=farm_id,
                    zone_id=zone_id,
                    observation_type="rainfall",
                    source=source_name,
                    observed_at=ts,
                    value=p_clean,
                    unit="mm",
                    metadata={
                        "period": "1h",
                        "model": "open_meteo",
                        "temperature_c": t_val,
                        "humidity_pct": rh_clean,
                    },
                )
            )

    weather_features = aggregate_hourly_weather(
        hourly_readings=hourly_readings,
        window_type=WeatherWindowType.DAILY_SUMMARY if count <= 24 else WeatherWindowType.HOURLY,
        source_provider=source_name,
        provenance_type=provenance,
        irradiance_type=SolarIrradianceType.INTERVAL_MEAN,
        wind_height_provenance=MeasurementHeightProvenance.PROVIDER_REPORTED,
    )

    observations.append(
        ObservationCreate(
            farm_id=farm_id,
            zone_id=zone_id,
            observation_type="weather",
            source=source_name,
            observed_at=weather_features.observed_at,
            value=weather_features.temperature_mean_c,
            unit="°C",
            metadata={
                "precipitation_mm": weather_features.precipitation_mm,
                "temp_min_c": weather_features.temperature_min_c,
                "temp_max_c": weather_features.temperature_max_c,
                "humidity_mean_pct": weather_features.relative_humidity_mean_pct,
                "wind_speed_m_s": weather_features.wind_speed_mean_m_s,
                "solar_radiation_mj_m2_day": weather_features.solar_radiation_mj_m2_day,
                "readings_count": count,
                "window_start": weather_features.window_start.isoformat(),
                "window_end": weather_features.window_end.isoformat(),
            },
        )
    )

    return observations, weather_features
