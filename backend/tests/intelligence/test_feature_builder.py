"""Tests for the central multimodal feature builder and data-quality synthesis."""

from datetime import date, datetime, timezone, timedelta
import pytest

from backend.app.intelligence.features.crop import create_crop_features
from backend.app.intelligence.features.feature_builder import (
    MultimodalZoneFeatureSet,
    build_zone_feature_set,
)
from backend.app.intelligence.features.soil import create_soil_features
from backend.app.intelligence.features.vegetation import ZoneVegetationFeatures
from backend.app.intelligence.features.weather import WeatherFeatures
from backend.app.intelligence.types import (
    DataQualityStatus,
    ProvenanceType,
    SoilTextureClass,
    WeatherWindowType,
)


@pytest.fixture
def fresh_timestamp():
    return datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)


@pytest.fixture
def mock_vegetation(fresh_timestamp):
    return ZoneVegetationFeatures(
        zone_id="ZONE_01",
        scene_id="S2A_20261101",
        source_provider="Copernicus Sentinel-2 L2A",
        observed_at=fresh_timestamp,
        provenance_type=ProvenanceType.SATELLITE_DERIVED,
        ndvi_mean=0.68,
        ndvi_median=0.70,
        ndvi_min=0.55,
        ndvi_max=0.80,
        ndvi_std=0.06,
        valid_observation_fraction=1.0,
        total_pixels_in_geometry=50,
        valid_vegetation_pixel_count=50,
        quality_status=DataQualityStatus.GOOD,
        is_stale=False,
    )


@pytest.fixture
def mock_weather(fresh_timestamp):
    return WeatherFeatures(
        source_provider="Open-Meteo",
        provenance_type=ProvenanceType.PROVIDER_MODELLED,
        window_type=WeatherWindowType.DAILY_SUMMARY,
        window_start=fresh_timestamp - timedelta(days=1),
        window_end=fresh_timestamp,
        observed_at=fresh_timestamp,
        precipitation_mm=5.0,
        temperature_min_c=18.0,
        temperature_max_c=32.0,
        temperature_mean_c=25.0,
        relative_humidity_mean_pct=65.0,
        wind_speed_mean_m_s=2.5,
        solar_radiation_mj_m2_day=22.0,
        quality_status=DataQualityStatus.GOOD,
        is_stale=False,
    )


@pytest.fixture
def mock_soil(fresh_timestamp):
    return create_soil_features(
        source_provider="FDR Probe 1",
        provenance_type=ProvenanceType.SENSOR_MEASURED,
        observed_at=fresh_timestamp,
        soil_moisture_m3_m3=0.25,
        soil_texture=SoilTextureClass.CLAY_LOAM,
        field_capacity_m3_m3=0.34,
        wilting_point_m3_m3=0.16,
    )


@pytest.fixture
def mock_crop(fresh_timestamp):
    return create_crop_features(
        crop_type="wheat",
        observed_at=fresh_timestamp,
        planting_date=date(2026, 10, 1),
        growth_stage="development",
    )


def test_complete_multimodal_feature_integration(
    fresh_timestamp,
    mock_vegetation,
    mock_weather,
    mock_soil,
    mock_crop,
):
    """Verify end-to-end integration when all multimodal features are present, fresh, and valid."""
    feature_set: MultimodalZoneFeatureSet = build_zone_feature_set(
        zone_id="ZONE_01",
        farm_id="FARM_PUNE_01",
        as_of_time=fresh_timestamp,
        vegetation_features=mock_vegetation,
        weather_features=mock_weather,
        soil_features=mock_soil,
        crop_features=mock_crop,
    )

    assert feature_set.zone_id == "ZONE_01"
    assert feature_set.farm_id == "FARM_PUNE_01"
    assert feature_set.overall_quality == DataQualityStatus.GOOD
    assert feature_set.missing_evidence == []

    # Provenance audit
    assert feature_set.provenance_summary["vegetation"] == ProvenanceType.SATELLITE_DERIVED
    assert feature_set.provenance_summary["weather"] == ProvenanceType.PROVIDER_MODELLED
    assert feature_set.provenance_summary["soil"] == ProvenanceType.SENSOR_MEASURED
    assert feature_set.provenance_summary["crop"] == ProvenanceType.FARMER_ENTERED

    # Freshness audit
    assert feature_set.freshness_summary["vegetation"] == True
    assert feature_set.freshness_summary["weather"] == True
    assert feature_set.freshness_summary["soil"] == True
    assert feature_set.freshness_summary["crop"] == True


def test_partial_evidence_handling(fresh_timestamp, mock_vegetation, mock_weather):
    """Verify that absent soil or crop evidence is audited and yields PARTIAL quality."""
    feature_set = build_zone_feature_set(
        zone_id="ZONE_01",
        as_of_time=fresh_timestamp,
        vegetation_features=mock_vegetation,
        weather_features=mock_weather,
        soil_features=None,
        crop_features=None,
    )

    assert feature_set.overall_quality == DataQualityStatus.PARTIAL
    assert set(feature_set.missing_evidence) == {"soil", "crop"}
    assert feature_set.soil is None
    assert feature_set.crop is None


def test_insufficient_evidence_when_both_dynamic_drivers_missing(fresh_timestamp, mock_soil):
    """Verify that missing both vegetation and weather yields INSUFFICIENT quality."""
    feature_set = build_zone_feature_set(
        zone_id="ZONE_01",
        as_of_time=fresh_timestamp,
        vegetation_features=None,
        weather_features=None,
        soil_features=mock_soil,
    )

    assert feature_set.overall_quality == DataQualityStatus.INSUFFICIENT
    assert any("both satellite and weather data are absent" in c for c in feature_set.quality_caveats)


def test_temporal_misalignment_detection(fresh_timestamp, mock_vegetation, mock_weather):
    """Verify that large time gaps between satellite and weather observations trigger explicit caveats."""
    # Satellite acquired on 2026-10-01 (14 days earlier than weather)
    stale_veg_time = fresh_timestamp - timedelta(days=14)
    veg_misaligned = mock_vegetation.model_copy(update={"observed_at": stale_veg_time})

    feature_set = build_zone_feature_set(
        zone_id="ZONE_01",
        as_of_time=fresh_timestamp,
        vegetation_features=veg_misaligned,
        weather_features=mock_weather,
    )

    assert any("Temporal misalignment" in c for c in feature_set.quality_caveats)
    assert any("diverge by 14.0 days" in c for c in feature_set.quality_caveats)


def test_quality_propagation_stale_and_suspect(fresh_timestamp, mock_vegetation, mock_weather, mock_soil):
    """Verify that stale and suspect flags propagate deterministically to overall quality."""
    # Case 1: Stale vegetation -> overall STALE
    stale_veg = mock_vegetation.model_copy(update={"is_stale": True, "quality_status": DataQualityStatus.STALE})
    feature_set_stale = build_zone_feature_set(
        zone_id="ZONE_01",
        as_of_time=fresh_timestamp,
        vegetation_features=stale_veg,
        weather_features=mock_weather,
    )
    assert feature_set_stale.overall_quality == DataQualityStatus.STALE

    # Case 2: Suspect soil sensor -> overall SUSPECT
    suspect_soil = mock_soil.model_copy(update={"quality_status": DataQualityStatus.SUSPECT})
    feature_set_suspect = build_zone_feature_set(
        zone_id="ZONE_01",
        as_of_time=fresh_timestamp,
        vegetation_features=mock_vegetation,
        weather_features=mock_weather,
        soil_features=suspect_soil,
    )
    assert feature_set_suspect.overall_quality == DataQualityStatus.SUSPECT


def test_zone_id_blank_validation(fresh_timestamp):
    """Verify that an empty or whitespace zone_id raises ValueError."""
    with pytest.raises(ValueError, match="zone_id cannot be empty or blank"):
        build_zone_feature_set(zone_id="   ", as_of_time=fresh_timestamp)


def test_itemized_provenance_and_domain_quality_segregation(
    fresh_timestamp,
    mock_vegetation,
    mock_weather,
    mock_soil,
    mock_crop,
):
    """Verify itemized provenance preservation and clean distinction between missing, stale, and suspect."""
    feature_set = build_zone_feature_set(
        zone_id="ZONE_01",
        farm_id="FARM_01",
        as_of_time=fresh_timestamp,
        vegetation_features=mock_vegetation,
        weather_features=mock_weather,
        soil_features=mock_soil,
        crop_features=mock_crop,
    )

    # 1. Provisional policy flag
    assert feature_set.is_provisional_freshness_applied == True

    # 2. Itemized provenance check for all modalities
    assert "vegetation" in feature_set.itemized_provenance
    assert feature_set.itemized_provenance["vegetation"]["source_provider"] == "Copernicus Sentinel-2 L2A"
    assert feature_set.itemized_provenance["vegetation"]["total_pixels_in_geometry"] == 50

    assert "weather" in feature_set.itemized_provenance
    assert feature_set.itemized_provenance["weather"]["source_provider"] == "Open-Meteo"
    assert feature_set.itemized_provenance["weather"]["wind_measurement_height_m"] == 10.0

    assert "soil" in feature_set.itemized_provenance
    assert feature_set.itemized_provenance["soil"]["source_provider"] == "FDR Probe 1"

    assert "crop" in feature_set.itemized_provenance
    assert feature_set.itemized_provenance["crop"]["crop_type"] == "wheat"

    # 3. Domain qualities and clean status segregation
    assert feature_set.domain_qualities["vegetation"] == DataQualityStatus.GOOD
    assert feature_set.domain_qualities["weather"] == DataQualityStatus.GOOD
    assert feature_set.domain_qualities["soil"] == DataQualityStatus.GOOD
    assert feature_set.domain_qualities["crop"] == DataQualityStatus.GOOD
    assert feature_set.stale_domains == []
    assert feature_set.suspect_domains == []
    assert feature_set.missing_evidence == []


def test_missing_stale_suspect_segregation(fresh_timestamp, mock_vegetation, mock_weather, mock_soil):
    """Verify missing, stale, and suspect domains are cleanly distinguished without arbitrary scores."""
    stale_weather = mock_weather.model_copy(update={"is_stale": True, "quality_status": DataQualityStatus.STALE})
    suspect_soil = mock_soil.model_copy(update={"quality_status": DataQualityStatus.SUSPECT})

    feature_set = build_zone_feature_set(
        zone_id="ZONE_01",
        as_of_time=fresh_timestamp,
        vegetation_features=mock_vegetation,
        weather_features=stale_weather,
        soil_features=suspect_soil,
        crop_features=None,  # Missing modality
    )

    # Missing vs Stale vs Suspect must be completely segregated
    assert feature_set.missing_evidence == ["crop"]
    assert feature_set.stale_domains == ["weather"]
    assert feature_set.suspect_domains == ["soil"]

    # Overall quality must follow deterministic hierarchy (SUSPECT overrides STALE)
    assert feature_set.overall_quality == DataQualityStatus.SUSPECT


