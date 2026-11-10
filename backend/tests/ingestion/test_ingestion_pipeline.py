"""Integration tests for end-to-end ingestion pipeline and intelligence connection."""

from datetime import datetime, timezone
import uuid
import pytest
from sqlalchemy.orm import Session

from app.ingestion.pipelines.pipeline import IngestionPipeline
from app.models.farm import Farm, FarmZone
from app.models.observation import Observation
from app.models.user import User
from app.intelligence.features.crop import CropFeatures
from app.intelligence.types import (
    DataQualityStatus,
    ProvenanceType,
    SoilTextureClass,
    SpatialQualityStatus,
    ZoneRasterStats,
)


@pytest.fixture
def test_farm_and_zone(db_session: Session) -> tuple[Farm, FarmZone]:
    """Create test farm and zone in database."""
    user = User(
        email=f"ingest_test_{uuid.uuid4().hex[:6]}@farmshield.ai",
        full_name="Ingestion Test Farmer",
        hashed_password="TestPassword123!",
        role="farmer",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    farm = Farm(
        owner_id=user.id,
        name="Baramati Demo Farm",
        crop_type="sugarcane",
        boundary="SRID=4326;MULTIPOLYGON(((74.58 18.15, 74.59 18.15, 74.59 18.16, 74.58 18.16, 74.58 18.15)))",
        area_hectares=10.0,
        location_name="Baramati, Pune",
    )
    db_session.add(farm)
    db_session.commit()
    db_session.refresh(farm)

    zone = FarmZone(
        farm_id=farm.id,
        zone_name="Zone A - Sugarcane North",
        zone_code=f"ZA_{uuid.uuid4().hex[:4]}",
        boundary="SRID=4326;POLYGON((74.581 18.151, 74.589 18.151, 74.589 18.159, 74.581 18.159, 74.581 18.151))",
        area_hectares=2.5,
    )
    db_session.add(zone)
    db_session.commit()
    db_session.refresh(zone)

    return farm, zone


def test_pipeline_weather_ingest_and_persist(db_session: Session, test_farm_and_zone: tuple[Farm, FarmZone]):
    """Verify live/fallback weather ingestion stores observations in DB and produces WeatherFeatures."""
    farm, zone = test_farm_and_zone
    pipeline = IngestionPipeline()

    persisted, weather_feats, soil_feats = pipeline.ingest_weather_for_coordinates(
        latitude=18.15,
        longitude=74.58,
        farm_id=farm.id,
        zone_id=zone.id,
        db=db_session,
        forecast_days=1,
    )

    assert len(persisted) > 0
    assert weather_feats is not None
    assert weather_feats.source_provider == "Open-Meteo Forecast API"
    assert weather_feats.provenance_type == ProvenanceType.PROVIDER_MODELLED
    assert weather_feats.temperature_mean_c is not None
    assert weather_feats.precipitation_mm is not None
    assert weather_feats.quality_status in [DataQualityStatus.GOOD, DataQualityStatus.PARTIAL]

    # Verify observations in database
    db_obs = db_session.query(Observation).filter(Observation.farm_id == farm.id).all()
    assert len(db_obs) >= len(persisted)


def test_pipeline_satellite_ingest_and_persist(db_session: Session, test_farm_and_zone: tuple[Farm, FarmZone]):
    """Verify satellite ingestion with NDVI stats stores observations and produces ZoneVegetationFeatures."""
    farm, zone = test_farm_and_zone
    pipeline = IngestionPipeline()

    ndvi_stats = ZoneRasterStats(
        index_name="NDVI",
        mean=0.58,
        median=0.57,
        min=0.40,
        max=0.75,
        std=0.07,
        total_pixels_in_geometry=80,
        valid_pixel_count=76,
        valid_pixel_fraction=76 / 80,
        min_valid_fraction_threshold=0.5,
        quality_status=SpatialQualityStatus.GOOD,
    )

    persisted, veg_feats = pipeline.ingest_satellite_for_bbox(
        bbox=[74.58, 18.15, 74.59, 18.16],
        start_date="2024-10-01",
        end_date="2024-11-01",
        farm_id=farm.id,
        zone_id=zone.id,
        db=db_session,
        ndvi_stats=ndvi_stats,
    )

    assert veg_feats is not None
    assert veg_feats.provenance_type == ProvenanceType.SATELLITE_DERIVED
    assert veg_feats.ndvi_mean == 0.58

    db_veg_obs = db_session.query(Observation).filter(
        Observation.farm_id == farm.id,
        Observation.observation_type == "vegetation_index",
    ).first()
    assert db_veg_obs is not None
    assert db_veg_obs.value == 0.58


def test_pipeline_connect_to_multimodal_feature_builder(db_session: Session, test_farm_and_zone: tuple[Farm, FarmZone]):
    """Verify normalized pipeline outputs assemble directly into MultimodalZoneFeatureSet."""
    farm, zone = test_farm_and_zone
    pipeline = IngestionPipeline()

    _, weather_feats, soil_feats = pipeline.ingest_weather_for_coordinates(
        latitude=18.15,
        longitude=74.58,
        farm_id=farm.id,
        zone_id=zone.id,
        db=db_session,
        forecast_days=1,
    )

    _, soil_sensor_feats = pipeline.ingest_soil_sensor_reading(
        sensor_id="PROBE-01",
        depth_min_cm=0.0,
        depth_max_cm=30.0,
        volumetric_water_content=0.27,
        observed_at=datetime.now(timezone.utc),
        farm_id=farm.id,
        zone_id=zone.id,
        db=db_session,
    )

    crop_feats = CropFeatures(
        crop_type="sugarcane",
        growth_stage="mid_season",
        planting_date=datetime(2026, 6, 1, tzinfo=timezone.utc).date(),
        rooting_depth_m=1.0,
        observed_at=datetime.now(timezone.utc),
        quality_status=DataQualityStatus.GOOD,
    )

    # Assemble multimodal zone feature set
    feature_set = pipeline.build_multimodal_features_for_zone(
        zone_id=str(zone.id),
        farm_id=str(farm.id),
        weather_features=weather_feats,
        soil_features=soil_sensor_feats,
        crop_features=crop_feats,
    )

    assert feature_set.zone_id == str(zone.id)
    assert feature_set.farm_id == str(farm.id)
    assert feature_set.weather is not None
    assert feature_set.soil is not None
    assert feature_set.crop is not None
    assert feature_set.overall_quality in [DataQualityStatus.GOOD, DataQualityStatus.PARTIAL]
    assert feature_set.soil.provenance_type == ProvenanceType.SENSOR_MEASURED
