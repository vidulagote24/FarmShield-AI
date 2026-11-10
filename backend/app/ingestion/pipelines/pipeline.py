"""Orchestrated data ingestion pipeline for farms and zones.

Unifies provider retrieval, normalizer validation, database persistence (Chaitanya's
Observation entities), and automatic connection to the multimodal feature builder
(Bhavikesh's intelligence engine).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy.orm import Session

from app.ingestion.normalizers.satellite_normalizer import normalize_sentinel2_vegetation
from app.ingestion.normalizers.soil_normalizer import (
    normalize_open_meteo_soil_moisture,
    normalize_sensor_soil_reading,
)
from app.ingestion.normalizers.weather_normalizer import normalize_open_meteo_weather
from app.ingestion.providers.open_meteo import OpenMeteoProvider
from app.ingestion.providers.sentinel2_stac import Sentinel2STACProvider
from app.ingestion.providers.soil_provider import SoilMeasurementProvider
from app.models.observation import Observation
from app.models.farm import Farm, FarmZone
from app.services.observation_service import bulk_create_observations
from app.intelligence.features.crop import CropFeatures
from app.intelligence.features.feature_builder import (
    MultimodalZoneFeatureSet,
    build_zone_feature_set,
)
from app.intelligence.features.soil import SoilFeatures
from app.intelligence.features.vegetation import ZoneVegetationFeatures
from app.intelligence.features.weather import WeatherFeatures
from app.intelligence.types import SoilTextureClass, ZoneRasterStats


class IngestionPipeline:
    """Orchestrator for end-to-end meteorological, satellite, and soil ingestion."""

    def __init__(
        self,
        weather_provider: Optional[OpenMeteoProvider] = None,
        satellite_provider: Optional[Sentinel2STACProvider] = None,
        soil_provider: Optional[SoilMeasurementProvider] = None,
    ) -> None:
        self.weather_provider = weather_provider or OpenMeteoProvider()
        self.satellite_provider = satellite_provider or Sentinel2STACProvider()
        self.soil_provider = soil_provider or SoilMeasurementProvider()

    def ingest_weather_for_coordinates(
        self,
        latitude: float,
        longitude: float,
        farm_id: Optional[uuid.UUID] = None,
        zone_id: Optional[uuid.UUID] = None,
        db: Optional[Session] = None,
        forecast_days: int = 3,
        fallback_fixture: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Observation], WeatherFeatures, Optional[SoilFeatures]]:
        """Fetch, normalize, persist, and return weather and modelled soil features."""
        fetch_res = self.weather_provider.fetch_forecast(
            latitude=latitude,
            longitude=longitude,
            forecast_days=forecast_days,
            fallback_fixture=fallback_fixture,
        )

        if fetch_res.status_code != 200:
            raise RuntimeError(f"Weather provider error: {fetch_res.error_message}")

        obs_creates, weather_features = normalize_open_meteo_weather(
            raw_payload=fetch_res.payload,
            farm_id=farm_id,
            zone_id=zone_id,
            source_name="Open-Meteo Forecast API",
        )

        soil_obs, soil_features = normalize_open_meteo_soil_moisture(
            raw_weather_payload=fetch_res.payload,
            farm_id=farm_id,
            zone_id=zone_id,
        )

        persisted_records: List[Observation] = []
        if db is not None and farm_id is not None:
            batch = obs_creates + soil_obs
            if batch:
                persisted_records = bulk_create_observations(
                    db=db,
                    farm_id=farm_id,
                    observations_in=batch,
                )

        return persisted_records, weather_features, soil_features

    def ingest_satellite_for_bbox(
        self,
        bbox: List[float],
        start_date: str,
        end_date: str,
        farm_id: Optional[uuid.UUID] = None,
        zone_id: Optional[uuid.UUID] = None,
        db: Optional[Session] = None,
        max_cloud_cover_pct: float = 40.0,
        ndvi_stats: Optional[ZoneRasterStats] = None,
        ndmi_stats: Optional[ZoneRasterStats] = None,
        fallback_fixture: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Observation], Optional[ZoneVegetationFeatures]]:
        """Search Sentinel-2 scenes, normalize metadata/indices, persist, and return vegetation features."""
        fetch_res = self.satellite_provider.search_scenes(
            bbox=bbox,
            start_date=start_date,
            end_date=end_date,
            max_cloud_cover_pct=max_cloud_cover_pct,
            fallback_fixture=fallback_fixture,
        )

        if fetch_res.status_code != 200:
            raise RuntimeError(f"Satellite provider error: {fetch_res.error_message}")

        features_list = fetch_res.payload.get("features", [])
        if not features_list:
            return [], None

        # Take most recent matching scene
        best_scene = features_list[0]
        obs_creates, veg_features = normalize_sentinel2_vegetation(
            stac_item=best_scene,
            ndvi_stats=ndvi_stats,
            ndmi_stats=ndmi_stats,
            farm_id=farm_id,
            zone_id=zone_id,
        )

        persisted_records: List[Observation] = []
        if db is not None and farm_id is not None:
            if obs_creates:
                persisted_records = bulk_create_observations(
                    db=db,
                    farm_id=farm_id,
                    observations_in=obs_creates,
                )

        return persisted_records, veg_features

    def ingest_soil_sensor_reading(
        self,
        sensor_id: str,
        depth_min_cm: float,
        depth_max_cm: float,
        volumetric_water_content: float,
        observed_at: datetime,
        farm_id: Optional[uuid.UUID] = None,
        zone_id: Optional[uuid.UUID] = None,
        db: Optional[Session] = None,
        field_capacity_m3_m3: float = 0.35,
        wilting_point_m3_m3: float = 0.18,
        soil_texture: SoilTextureClass = SoilTextureClass.CLAY_LOAM,
    ) -> Tuple[List[Observation], SoilFeatures]:
        """Ingest and persist in-situ soil moisture sensor reading."""
        fetch_res = self.soil_provider.ingest_sensor_reading(
            sensor_id=sensor_id,
            depth_min_cm=depth_min_cm,
            depth_max_cm=depth_max_cm,
            volumetric_water_content=volumetric_water_content,
            observed_at=observed_at,
        )
        obs_creates, soil_features = normalize_sensor_soil_reading(
            payload=fetch_res.payload,
            farm_id=farm_id,
            zone_id=zone_id,
            field_capacity_m3_m3=field_capacity_m3_m3,
            wilting_point_m3_m3=wilting_point_m3_m3,
            soil_texture=soil_texture,
        )

        persisted_records: List[Observation] = []
        if db is not None and farm_id is not None:
            if obs_creates:
                persisted_records = bulk_create_observations(
                    db=db,
                    farm_id=farm_id,
                    observations_in=obs_creates,
                )

        return persisted_records, soil_features

    def build_multimodal_features_for_zone(
        self,
        zone_id: str,
        farm_id: Optional[str] = None,
        vegetation_features: Optional[ZoneVegetationFeatures] = None,
        weather_features: Optional[WeatherFeatures] = None,
        soil_features: Optional[SoilFeatures] = None,
        crop_features: Optional[CropFeatures] = None,
        as_of_time: Optional[datetime] = None,
    ) -> MultimodalZoneFeatureSet:
        """Connect all normalized evidence streams into the intelligence MultimodalZoneFeatureSet."""
        return build_zone_feature_set(
            zone_id=zone_id,
            farm_id=farm_id,
            as_of_time=as_of_time,
            vegetation_features=vegetation_features,
            weather_features=weather_features,
            soil_features=soil_features,
            crop_features=crop_features,
        )
