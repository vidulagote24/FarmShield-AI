"""Provider clients for external meteorological, satellite, and soil data sources."""

from app.ingestion.providers.base import BaseProvider, ProviderFetchResult
from app.ingestion.providers.open_meteo import OpenMeteoProvider
from app.ingestion.providers.sentinel2_stac import Sentinel2STACProvider
from app.ingestion.providers.soil_provider import SoilMeasurementProvider

__all__ = [
    "BaseProvider",
    "ProviderFetchResult",
    "OpenMeteoProvider",
    "Sentinel2STACProvider",
    "SoilMeasurementProvider",
]
