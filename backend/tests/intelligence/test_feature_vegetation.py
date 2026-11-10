"""Tests for vegetation feature extraction, statistics, and multi-temporal trends."""

from datetime import datetime, timezone, timedelta
import numpy as np
import pytest
from shapely.geometry import box, Polygon

from backend.app.intelligence.config import GeospatialConfig
from backend.app.intelligence.features.vegetation import (
    ZoneVegetationFeatures,
    VegetationTrendResult,
    compute_vegetation_trend,
    extract_vegetation_features_for_zone,
)
from backend.app.intelligence.geospatial.raster_processing import GeoRasterGrid
from backend.app.intelligence.types import (
    BoundingBox,
    DataQualityStatus,
    ProvenanceType,
    RasterMetadata,
)


@pytest.fixture
def synthetic_vegetation_grids():
    """Create aligned synthetic NDVI, NDMI, and SCL grids for testing.

    Grid: 4x4 pixels over [73.80, 73.84] Lon, [18.50, 18.54] Lat.
    Resolution = 0.01 deg (~1.1 km).
    """
    bounds = BoundingBox(min_x=73.80, min_y=18.50, max_x=73.84, max_y=18.54, crs="EPSG:4326")
    acq_time = datetime(2026, 11, 1, 10, 30, tzinfo=timezone.utc)

    meta = RasterMetadata(
        scene_id="S2A_MSIL2A_20261101_TEST",
        acquisition_time=acq_time,
        crs="EPSG:4326",
        resolution_m=10.0,
        bounds=bounds,
        rows=4,
        cols=4,
    )

    # NDVI: 16 pixels
    # Row 0: [0.70, 0.72, 0.74, 0.76]
    # Row 1: [0.60, 0.62, 0.64, 0.66]
    # Row 2: [0.20, 0.22, 0.24, 0.26] -> will be assigned SCL 5 (bare soil)
    # Row 3: [-0.30, -0.20, 0.80, 0.82] -> (3,0) water SCL 6, (3,1) cloud SCL 8, (3,2:3) veg SCL 4
    ndvi_data = np.array([
        [0.70, 0.72, 0.74, 0.76],
        [0.60, 0.62, 0.64, 0.66],
        [0.20, 0.22, 0.24, 0.26],
        [-0.30, -0.20, 0.80, 0.82],
    ], dtype=np.float32)

    # NDMI: canopy water index
    ndmi_data = np.array([
        [0.40, 0.42, 0.44, 0.46],
        [0.30, 0.32, 0.34, 0.36],
        [0.05, 0.06, 0.07, 0.08],
        [-0.40, 0.00, 0.50, 0.52],
    ], dtype=np.float32)

    # SCL:
    # Row 0 & 1: all 4 (Vegetation) -> 8 pixels
    # Row 2: all 5 (Bare Soil) -> 4 pixels
    # Row 3: [6 (Water), 8 (Cloud), 4 (Vegetation), 4 (Vegetation)] -> 2 veg, 1 water, 1 cloud
    scl_data = np.array([
        [4, 4, 4, 4],
        [4, 4, 4, 4],
        [5, 5, 5, 5],
        [6, 8, 4, 4],
    ], dtype=np.uint8)

    ndvi_grid = GeoRasterGrid(ndvi_data, meta)
    ndmi_grid = GeoRasterGrid(ndmi_data, meta)
    scl_grid = GeoRasterGrid(scl_data.astype(np.float32), meta)

    return ndvi_grid, ndmi_grid, scl_grid


def test_hand_calculated_vegetation_statistics(synthetic_vegetation_grids):
    """Verify hand-calculated NDVI and NDMI statistics with strict SCL separation.

    In the synthetic grid (16 pixels total):
    Vegetation pixels (SCL 4):
    Row 0: 0.70, 0.72, 0.74, 0.76
    Row 1: 0.60, 0.62, 0.64, 0.66
    Row 3: (3, 2) 0.80, (3, 3) 0.82
    Total valid vegetation pixels = 10 pixels.

    Excluded from vegetation canopy stats:
    - Row 2: bare soil (0.20, 0.22, 0.24, 0.26)
    - Row 3, Col 0: water (-0.30)
    - Row 3, Col 1: cloud (-0.20)

    Hand calculation for NDVI of the 10 vegetation pixels:
    Values: [0.60, 0.62, 0.64, 0.66, 0.70, 0.72, 0.74, 0.76, 0.80, 0.82]
    Sum = 7.06
    Mean = 7.06 / 10 = 0.7060
    Median (middle 2 are 0.70 and 0.72) = (0.70 + 0.72) / 2 = 0.7100
    Min = 0.6000
    Max = 0.8200
    p10: index 0.9 -> 0.60 + 0.9 * (0.62 - 0.60) = 0.6180 (linear)
    p25: index 2.25 -> 0.64 + 0.25 * (0.66 - 0.64) = 0.6450
    p75: index 6.75 -> 0.74 + 0.75 * (0.76 - 0.74) = 0.7550
    p90: index 8.1 -> 0.80 + 0.1 * (0.82 - 0.80) = 0.8020
    """
    ndvi_grid, ndmi_grid, scl_grid = synthetic_vegetation_grids

    # Zone covers the entire 4x4 grid
    zone_poly = box(73.80, 18.50, 73.84, 18.54)

    features = extract_vegetation_features_for_zone(
        zone_geom=zone_poly,
        ndvi_raster=ndvi_grid,
        ndmi_raster=ndmi_grid,
        scl_raster=scl_grid,
        zone_id="ZONE_HAND_CALC",
        as_of_time=datetime(2026, 11, 2, tzinfo=timezone.utc),
    )

    assert features.zone_id == "ZONE_HAND_CALC"
    assert features.scene_id == "S2A_MSIL2A_20261101_TEST"
    assert features.source_provider == "Copernicus Sentinel-2 L2A"
    assert features.provenance_type == ProvenanceType.SATELLITE_DERIVED
    assert features.quality_status == DataQualityStatus.GOOD
    assert features.is_stale == False

    # Pixel Counts
    assert features.total_pixels_in_geometry == 16
    assert features.valid_vegetation_pixel_count == 10

    # Hand-calculated NDVI checks
    assert pytest.approx(features.ndvi_mean, abs=1e-4) == 0.7060
    assert pytest.approx(features.ndvi_median, abs=1e-4) == 0.7100
    assert pytest.approx(features.ndvi_min, abs=1e-4) == 0.6000
    assert pytest.approx(features.ndvi_max, abs=1e-4) == 0.8200
    assert pytest.approx(features.ndvi_p10, abs=1e-3) == 0.6180
    assert pytest.approx(features.ndvi_p25, abs=1e-3) == 0.6450
    assert pytest.approx(features.ndvi_p75, abs=1e-3) == 0.7550
    assert pytest.approx(features.ndvi_p90, abs=1e-3) == 0.8020

    # Fractions:
    # Vegetation: 10 / 16 = 0.6250
    # Bare soil: 4 / 16 = 0.2500
    # Water: 1 / 16 = 0.0625
    # Cloud: 1 / 16 = 0.0625
    # Clear observation fraction: (10 + 4 + 1) / 16 = 15 / 16 = 0.9375
    assert pytest.approx(features.vegetation_coverage_fraction, abs=1e-4) == 0.6250
    assert pytest.approx(features.bare_soil_fraction, abs=1e-4) == 0.2500
    assert pytest.approx(features.water_fraction, abs=1e-4) == 0.0625
    assert pytest.approx(features.cloud_fraction, abs=1e-4) == 0.0625
    assert pytest.approx(features.valid_observation_fraction, abs=1e-4) == 0.9375

    # Hand-calculated NDMI checks (over the 10 vegetation pixels)
    # NDMI values: [0.30, 0.32, 0.34, 0.36, 0.40, 0.42, 0.44, 0.46, 0.50, 0.52]
    # Sum = 4.06 -> Mean = 4.06 / 10 = 0.4060
    # Median = (0.40 + 0.42) / 2 = 0.4100
    assert pytest.approx(features.ndmi_mean, abs=1e-4) == 0.4060
    assert pytest.approx(features.ndmi_median, abs=1e-4) == 0.4100

    # Scientific caveats must be attached
    assert len(features.scientific_caveats) >= 4
    assert any("NDVI is a spectral greenness indicator" in c for c in features.scientific_caveats)
    assert any("NDMI reflects canopy water content" in c for c in features.scientific_caveats)


def test_staleness_flagging(synthetic_vegetation_grids):
    """Verify that observations older than configured freshness threshold are flagged stale."""
    ndvi_grid, _, _ = synthetic_vegetation_grids
    zone_poly = box(73.80, 18.50, 73.84, 18.54)

    # Scene was acquired 2026-11-01
    # Evaluation at 2026-11-20 (19 days later > 14 days default stale threshold)
    eval_time = datetime(2026, 11, 20, tzinfo=timezone.utc)

    features = extract_vegetation_features_for_zone(
        zone_geom=zone_poly,
        ndvi_raster=ndvi_grid,
        zone_id="ZONE_STALE",
        as_of_time=eval_time,
        stale_days=14.0,
    )

    assert features.is_stale == True
    assert features.quality_status == DataQualityStatus.STALE
    assert "exceeds 14.0d freshness threshold" in features.quality_note


def test_withholding_on_insufficient_valid_pixels(synthetic_vegetation_grids):
    """Verify numerical statistics are withheld when valid vegetation pixels fall below threshold."""
    ndvi_grid, _, scl_grid = synthetic_vegetation_grids

    # Small zone covering only 1 pixel (top-left corner)
    zone_tiny = box(73.80, 18.53, 73.81, 18.54)

    # Config requiring at least 3 pixels
    cfg = GeospatialConfig(min_pixel_count=3, min_valid_pixel_fraction=0.60)

    features = extract_vegetation_features_for_zone(
        zone_geom=zone_tiny,
        ndvi_raster=ndvi_grid,
        scl_raster=scl_grid,
        zone_id="ZONE_INSUFFICIENT",
        config=cfg,
    )

    # Numerical NDVI statistics MUST be None when criteria are not met
    assert features.valid_vegetation_pixel_count < 3
    assert features.ndvi_mean is None
    assert features.ndvi_median is None
    assert features.quality_status in {DataQualityStatus.PARTIAL, DataQualityStatus.SUSPECT}


def test_single_scene_temporal_trend_refusal(synthetic_vegetation_grids):
    """Verify scientific restriction: trend CANNOT be manufactured from a single observation."""
    ndvi_grid, _, _ = synthetic_vegetation_grids
    zone_poly = box(73.80, 18.50, 73.84, 18.54)

    single_obs = extract_vegetation_features_for_zone(
        zone_geom=zone_poly,
        ndvi_raster=ndvi_grid,
        zone_id="ZONE_TREND",
    )

    # Passing only 1 observation must return None
    trend = compute_vegetation_trend([single_obs])
    assert trend is None

    # Passing empty list must return None
    assert compute_vegetation_trend([]) is None


def test_multi_temporal_trend_calculation():
    """Verify multi-temporal vegetation trend calculation with hand-calculated deltas."""
    t0 = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc)  # 14 days later

    obs1 = ZoneVegetationFeatures(
        zone_id="ZONE_01",
        scene_id="SCENE_01",
        observed_at=t0,
        ndvi_mean=0.4500,
        valid_observation_fraction=1.0,
        total_pixels_in_geometry=20,
        valid_vegetation_pixel_count=20,
        quality_status=DataQualityStatus.GOOD,
    )

    obs2 = ZoneVegetationFeatures(
        zone_id="ZONE_01",
        scene_id="SCENE_02",
        observed_at=t1,
        ndvi_mean=0.6600,
        valid_observation_fraction=1.0,
        total_pixels_in_geometry=20,
        valid_vegetation_pixel_count=20,
        quality_status=DataQualityStatus.GOOD,
    )

    trend: VegetationTrendResult = compute_vegetation_trend([obs1, obs2])
    assert trend is not None
    assert trend.zone_id == "ZONE_01"
    assert trend.observation_count == 2
    assert pytest.approx(trend.delta_days, abs=1e-3) == 14.0
    # Delta NDVI = 0.6600 - 0.4500 = +0.2100
    assert pytest.approx(trend.delta_ndvi_mean, abs=1e-4) == 0.2100
    # Change rate per day = 0.2100 / 14.0 = +0.0150
    assert pytest.approx(trend.ndvi_change_rate_per_day, abs=1e-4) == 0.0150
    assert pytest.approx(trend.ndvi_rate_per_day, abs=1e-4) == 0.0150  # Property alias
    assert trend.trend_direction == "increasing"
    assert trend.is_material_change == True
    assert trend.is_significant == True  # Backward compatibility alias
    assert trend.earliest_quality_status == DataQualityStatus.GOOD
    assert trend.latest_quality_status == DataQualityStatus.GOOD
    assert trend.rate_method == "two_point_endpoint_finite_difference"


def test_cross_zone_comparability_rejection():
    """Verify that calculating a change rate between different zones raises ValueError."""
    t0 = datetime(2026, 10, 1, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 15, tzinfo=timezone.utc)

    obs_a = ZoneVegetationFeatures(
        zone_id="ZONE_A",
        scene_id="SCENE_01",
        observed_at=t0,
        ndvi_mean=0.50,
        valid_observation_fraction=1.0,
        total_pixels_in_geometry=10,
        valid_vegetation_pixel_count=10,
        quality_status=DataQualityStatus.GOOD,
    )
    obs_b = ZoneVegetationFeatures(
        zone_id="ZONE_B",
        scene_id="SCENE_02",
        observed_at=t1,
        ndvi_mean=0.60,
        valid_observation_fraction=1.0,
        total_pixels_in_geometry=10,
        valid_vegetation_pixel_count=10,
        quality_status=DataQualityStatus.GOOD,
    )

    with pytest.raises(ValueError, match="Cannot calculate vegetation change rate across different zones"):
        compute_vegetation_trend([obs_a, obs_b])


def test_temporal_separation_threshold():
    """Verify that observations separated by less than min_delta_days return None."""
    t0 = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 1, 18, 0, tzinfo=timezone.utc)  # 8 hours later (< 1.0 day)

    obs1 = ZoneVegetationFeatures(
        zone_id="ZONE_01",
        scene_id="SCENE_01",
        observed_at=t0,
        ndvi_mean=0.50,
        valid_observation_fraction=1.0,
        total_pixels_in_geometry=10,
        valid_vegetation_pixel_count=10,
        quality_status=DataQualityStatus.GOOD,
    )
    obs2 = ZoneVegetationFeatures(
        zone_id="ZONE_01",
        scene_id="SCENE_02",
        observed_at=t1,
        ndvi_mean=0.52,
        valid_observation_fraction=1.0,
        total_pixels_in_geometry=10,
        valid_vegetation_pixel_count=10,
        quality_status=DataQualityStatus.GOOD,
    )

    # With default min_delta_days=1.0, delta is 0.333 days -> returns None
    result = compute_vegetation_trend([obs1, obs2], min_delta_days=1.0)
    assert result is None


def test_vegetation_change_materiality_threshold():
    """Verify that is_material_change is an agronomic threshold check and NOT statistical significance.

    Per Phase 2.1.1:
    - delta_ndvi = 0.52 - 0.50 = +0.02.
    - With materiality_threshold = 0.05, is_material_change is False.
    - With materiality_threshold = 0.015, is_material_change is True.
    - Two-point finite difference endpoint rate is preserved without statistical inference.
    """
    t0 = datetime(2026, 10, 1, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 10, tzinfo=timezone.utc)  # 9 days

    obs1 = ZoneVegetationFeatures(
        zone_id="ZONE_01",
        scene_id="SCENE_01",
        observed_at=t0,
        ndvi_mean=0.50,
        valid_observation_fraction=1.0,
        total_pixels_in_geometry=10,
        valid_vegetation_pixel_count=10,
        quality_status=DataQualityStatus.GOOD,
    )
    obs2 = ZoneVegetationFeatures(
        zone_id="ZONE_01",
        scene_id="SCENE_02",
        observed_at=t1,
        ndvi_mean=0.52,
        valid_observation_fraction=1.0,
        total_pixels_in_geometry=10,
        valid_vegetation_pixel_count=10,
        quality_status=DataQualityStatus.GOOD,
    )

    # 1. Below 0.05 threshold -> is_material_change is False
    res_immaterial = compute_vegetation_trend([obs1, obs2], materiality_threshold=0.05)
    assert res_immaterial is not None
    assert res_immaterial.is_material_change == False
    assert res_immaterial.is_significant == False
    assert pytest.approx(res_immaterial.delta_ndvi_mean, abs=1e-4) == 0.02
    assert pytest.approx(res_immaterial.ndvi_change_rate_per_day, abs=1e-4) == 0.02 / 9.0

    # 2. Above 0.015 threshold -> is_material_change is True
    res_material = compute_vegetation_trend([obs1, obs2], materiality_threshold=0.015)
    assert res_material is not None
    assert res_material.is_material_change == True
    assert res_material.is_significant == True



