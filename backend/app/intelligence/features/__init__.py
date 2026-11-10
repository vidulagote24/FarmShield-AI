"""Multimodal feature engineering subpackage for FarmShield AI.

Transforms raw and normalized geospatial, satellite, weather, soil,
and crop context into structured, scientifically defensible features.
"""

from .crop import CropFeatures, create_crop_features
from .feature_builder import MultimodalZoneFeatureSet, build_zone_feature_set
from .soil import SoilFeatures, create_soil_features
from .vegetation import (
    VegetationTrendResult,
    ZoneVegetationFeatures,
    compute_vegetation_trend,
    extract_vegetation_features_for_zone,
)
from .weather import (
    HourlyWeatherReading,
    WeatherFeatures,
    aggregate_hourly_weather,
    kmh_to_ms,
    kwh_m2_to_mj_m2,
    ms_to_kmh,
    wm2_hourly_to_mj_m2,
)

__all__ = [
    "CropFeatures",
    "create_crop_features",
    "SoilFeatures",
    "create_soil_features",
    "ZoneVegetationFeatures",
    "VegetationTrendResult",
    "extract_vegetation_features_for_zone",
    "compute_vegetation_trend",
    "HourlyWeatherReading",
    "WeatherFeatures",
    "aggregate_hourly_weather",
    "kmh_to_ms",
    "ms_to_kmh",
    "wm2_hourly_to_mj_m2",
    "kwh_m2_to_mj_m2",
    "MultimodalZoneFeatureSet",
    "build_zone_feature_set",
]

