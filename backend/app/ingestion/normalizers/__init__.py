"""Data normalizers converting provider payloads to backend schemas and intelligence features."""

from app.ingestion.normalizers.satellite_normalizer import (
    SatelliteNormalizationError,
    normalize_sentinel2_vegetation,
)
from app.ingestion.normalizers.soil_normalizer import (
    SoilNormalizationError,
    normalize_open_meteo_soil_moisture,
    normalize_sensor_soil_reading,
)
from app.ingestion.normalizers.weather_normalizer import (
    WeatherNormalizationError,
    normalize_open_meteo_weather,
)

__all__ = [
    "WeatherNormalizationError",
    "normalize_open_meteo_weather",
    "SatelliteNormalizationError",
    "normalize_sentinel2_vegetation",
    "SoilNormalizationError",
    "normalize_sensor_soil_reading",
    "normalize_open_meteo_soil_moisture",
]
