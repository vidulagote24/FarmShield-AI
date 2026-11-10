"""Tests for raster grid alignment, multi-resolution resampling, and SCL masking."""

import numpy as np
import pytest

from backend.app.intelligence.geospatial.grid_alignment import (
    ResamplingMethod,
    SCL_BARE_SOIL_CLASSES,
    SCL_CLASS_DESCRIPTIONS,
    SCL_CLEAR_OBSERVATION_CLASSES,
    SCL_CONTAMINATION_CLASSES,
    SCL_CROP_VEGETATION_CLASSES,
    SCL_EXCLUDED_FOR_VEGETATION,
    SCL_USABLE_FOR_VEGETATION,
    SCL_VEGETATION_CLASSES,
    SCL_WATER_CLASSES,
    ZoneSCLBreakdown,
    calculate_aligned_ndmi,
    compute_zone_scl_breakdown,
    resample_raster_to_target,
    resample_scl_to_10m,
    validate_raster_alignment,
)
from backend.app.intelligence.geospatial.raster_processing import GeoRasterGrid, create_valid_mask
from backend.app.intelligence.types import BoundingBox, RasterMetadata


@pytest.fixture
def base_10m_grid():
    """Create a 4x4 grid at 10m nominal resolution in WGS84."""
    bounds = BoundingBox(min_x=73.80, min_y=18.50, max_x=73.84, max_y=18.54, crs="EPSG:4326")
    meta = RasterMetadata(
        scene_id="S2_TEST_10M",
        crs="EPSG:4326",
        resolution_m=10.0,
        bounds=bounds,
        rows=4,
        cols=4,
    )
    data = np.full((4, 4), 0.8, dtype=np.float32)
    return GeoRasterGrid(data, meta)


@pytest.fixture
def base_20m_grid():
    """Create a 2x2 grid at 20m nominal resolution sharing the exact same spatial bounding box."""
    bounds = BoundingBox(min_x=73.80, min_y=18.50, max_x=73.84, max_y=18.54, crs="EPSG:4326")
    meta = RasterMetadata(
        scene_id="S2_TEST_20M",
        crs="EPSG:4326",
        resolution_m=20.0,
        bounds=bounds,
        rows=2,
        cols=2,
    )
    data = np.full((2, 2), 0.2, dtype=np.float32)
    return GeoRasterGrid(data, meta)


def test_validate_raster_alignment_matching(base_10m_grid):
    """Verify that identical grids pass alignment validation."""
    is_aligned, reason = validate_raster_alignment(base_10m_grid, base_10m_grid)
    assert is_aligned is True
    assert reason is None


def test_validate_raster_alignment_resolution_mismatch(base_10m_grid, base_20m_grid):
    """Verify that resolution / dimension mismatch is detected."""
    is_aligned, reason = validate_raster_alignment(base_10m_grid, base_20m_grid)
    assert is_aligned is False
    assert "Dimension mismatch" in reason or "Pixel size mismatch" in reason


def test_scl_nearest_neighbor_resampling(base_10m_grid, base_20m_grid):
    """Verify that 20m categorical SCL resampled to 10m preserves discrete class integers."""
    # 2x2 SCL array with distinct discrete classes: 4 (vegetation), 5 (soil), 8 (cloud), 3 (shadow)
    scl_data = np.array([
        [4, 5],
        [8, 3],
    ], dtype=np.float32)
    scl_grid = GeoRasterGrid(scl_data, base_20m_grid.metadata)

    # Resample onto 4x4 10m grid
    resampled_scl = resample_scl_to_10m(scl_grid, base_10m_grid)

    assert resampled_scl.rows == 4
    assert resampled_scl.cols == 4

    # Every pixel must strictly remain one of the original discrete class codes {3, 4, 5, 8}
    unique_classes = set(np.unique(resampled_scl.data))
    assert unique_classes.issubset({3.0, 4.0, 5.0, 8.0})

    # Top-left 2x2 block must all be 4.0 (nearest neighbor expansion)
    assert np.all(resampled_scl.data[:2, :2] == 4.0)
    # Bottom-right 2x2 block must all be 3.0
    assert np.all(resampled_scl.data[2:, 2:] == 3.0)


def test_scl_class_policy_definitions():
    """Verify that SCL included and excluded classes match documented agronomic policy."""
    # Strict vegetation analysis must isolate Class 4 (general green vegetation)
    assert SCL_VEGETATION_CLASSES == {4}
    assert SCL_CROP_VEGETATION_CLASSES == {4}
    assert SCL_USABLE_FOR_VEGETATION == {4}

    # Verify Class 4 description indicates general green vegetation, not crop canopy
    assert "General green vegetation" in SCL_CLASS_DESCRIPTIONS[4]
    assert "does not distinguish crop" in SCL_CLASS_DESCRIPTIONS[4]

    # Verify Class 2 description accounts for Sentinel-2 processing baseline evolution:
    # Pre-PB 04.00: DARK_AREA_PIXELS; PB 04.00-05.10: DARK_FEATURES; PB 05.11+: CAST_SHADOW
    assert "DARK_AREA_PIXELS" in SCL_CLASS_DESCRIPTIONS[2]
    assert "DARK_FEATURES" in SCL_CLASS_DESCRIPTIONS[2]
    assert "CAST_SHADOW" in SCL_CLASS_DESCRIPTIONS[2]

    # Distinct categories must not be lumped into vegetation
    assert SCL_BARE_SOIL_CLASSES == {5}
    assert SCL_WATER_CLASSES == {6}

    # Clear surface observation includes clear ground/water
    assert SCL_CLEAR_OBSERVATION_CLASSES == {4, 5, 6}

    # Excluded: clouds (8, 9, 10), shadow (3), defective (1), nodata (0), snow (11), unclassified (7), cast shadows (2)
    assert 2 in SCL_CONTAMINATION_CLASSES  # Cast shadow / dark area
    assert 8 in SCL_CONTAMINATION_CLASSES  # Cloud medium
    assert 9 in SCL_CONTAMINATION_CLASSES  # Cloud high
    assert 10 in SCL_CONTAMINATION_CLASSES # Cirrus
    assert 3 in SCL_CONTAMINATION_CLASSES  # Cloud shadow
    assert 7 in SCL_CONTAMINATION_CLASSES  # Unclassified
    assert 0 in SCL_CONTAMINATION_CLASSES  # NoData
    assert 1 in SCL_CONTAMINATION_CLASSES  # Defective
    assert 11 in SCL_CONTAMINATION_CLASSES # Snow


def test_ndmi_native_vs_resampled(base_10m_grid, base_20m_grid):
    """Verify NDMI calculation between 10m NIR (B8) and 20m SWIR1 (B11)."""
    # NIR at 10m: 4x4 array of 0.60
    nir_10m_data = np.full((4, 4), 0.60, dtype=np.float32)
    nir_10m = GeoRasterGrid(nir_10m_data, base_10m_grid.metadata)

    # SWIR1 at 20m: 2x2 array of 0.20
    swir_20m_data = np.full((2, 2), 0.20, dtype=np.float32)
    swir_20m = GeoRasterGrid(swir_20m_data, base_20m_grid.metadata)

    # calculate_aligned_ndmi should downsample 10m NIR to 20m SWIR1 grid by default
    ndmi_res = calculate_aligned_ndmi(nir_10m, swir_20m, use_native_20m=True)

    assert ndmi_res.rows == 2
    assert ndmi_res.cols == 2
    # Expected: (0.6 - 0.2) / (0.6 + 0.2) = 0.4 / 0.8 = 0.5000
    assert np.allclose(ndmi_res.data, 0.5000, atol=1e-4)


def test_scl_separation_prevents_soil_and_water_contamination():
    """Verify that bare soil and water pixels do not contaminate vegetation NDVI statistics.

    Scenario:
    - Pixel (0, 0): Green vegetation, NDVI = 0.75, SCL = 4 (Vegetation)
    - Pixel (0, 1): Bare soil / tractor path, NDVI = 0.20, SCL = 5 (Bare soil)
    - Pixel (1, 0): Irrigation pond / puddle, NDVI = -0.30, SCL = 6 (Water)
    - Pixel (1, 1): Cloud shadow, NDVI = 0.10, SCL = 3 (Shadow)

    If classes 4, 5, 6 were lumped together, the mean NDVI would become:
        (0.75 + 0.20 - 0.30) / 3 = 0.2167 (severe false drought alarm!)

    With strict vegetation masking (vegetation_only=True):
        Only Class 4 is accepted -> Mean NDVI is strictly 0.7500.
    """
    ndvi_data = np.array([
        [0.75, 0.20],
        [-0.30, 0.10],
    ], dtype=np.float32)

    scl_data = np.array([
        [4, 5],
        [6, 3],
    ], dtype=np.uint8)

    # 1. Vegetation mask strictly isolates Class 4 (testing both vegetation_only and backward compat)
    veg_mask = create_valid_mask(ndvi_data, scl_layer=scl_data, vegetation_only=True)
    assert veg_mask[0, 0] == True   # Green vegetation
    assert veg_mask[0, 1] == False  # Bare soil excluded
    assert veg_mask[1, 0] == False  # Water excluded
    assert veg_mask[1, 1] == False  # Shadow excluded

    crop_mask_compat = create_valid_mask(ndvi_data, scl_layer=scl_data, crop_vegetation_only=True)
    assert np.array_equal(veg_mask, crop_mask_compat)

    valid_veg_ndvi = ndvi_data[veg_mask]
    assert len(valid_veg_ndvi) == 1
    assert pytest.approx(float(valid_veg_ndvi[0]), abs=1e-4) == 0.7500

    # 2. General clear-sky surface observation mask accepts {4, 5, 6}
    clear_mask = create_valid_mask(ndvi_data, scl_layer=scl_data, vegetation_only=False)
    assert clear_mask[0, 0] == True   # Vegetation is clear surface
    assert clear_mask[0, 1] == True   # Bare soil is clear surface
    assert clear_mask[1, 0] == True   # Water is clear surface
    assert clear_mask[1, 1] == False  # Shadow is contaminated


def test_compute_zone_scl_breakdown(base_10m_grid):
    """Verify detailed SCL land-cover breakdown reporting across a zone."""
    from shapely.geometry import box
    from backend.app.intelligence.geospatial.grid_alignment import compute_zone_scl_breakdown

    # 4x4 SCL grid:
    # 8 pixels of Vegetation (4)
    # 4 pixels of Bare Soil (5)
    # 2 pixels of Water (6)
    # 2 pixels of Cloud (8)
    scl_arr = np.array([
        [4, 4, 4, 4],
        [4, 4, 4, 4],
        [5, 5, 5, 5],
        [6, 6, 8, 8],
    ], dtype=np.float32)

    scl_raster = GeoRasterGrid(scl_arr, base_10m_grid.metadata)
    zone_poly = box(73.80, 18.50, 73.84, 18.54)

    breakdown = compute_zone_scl_breakdown(scl_raster, zone_poly)

    assert breakdown.total_pixels == 16
    assert breakdown.vegetation_pixels == 8
    assert pytest.approx(breakdown.vegetation_fraction, abs=1e-4) == 0.5000
    assert breakdown.bare_soil_pixels == 4
    assert pytest.approx(breakdown.bare_soil_fraction, abs=1e-4) == 0.2500
    assert breakdown.water_pixels == 2
    assert pytest.approx(breakdown.water_fraction, abs=1e-4) == 0.1250
    assert breakdown.cloud_pixels == 2
    assert pytest.approx(breakdown.cloud_fraction, abs=1e-4) == 0.1250


def test_all_scl_classes_mutually_exclusive_and_sum_to_one(base_10m_grid):
    """Verify that every SCL class (0 through 11 and invalid) is accounted for and sums to 1.0."""
    from shapely.geometry import box

    # 4x4 grid containing every class 0 to 11 plus invalid (15)
    # 0: NoData, 1: Defective, 2: Cast Shadow, 3: Cloud Shadow
    # 4: Vegetation, 5: Soil, 6: Water, 7: Unclassified
    # 8: Cloud Med, 9: Cloud High, 10: Cirrus, 11: Snow
    # 15: Invalid / Out-of-spec
    scl_arr = np.array([
        [0, 1, 2, 3],
        [4, 5, 6, 7],
        [8, 9, 10, 11],
        [4, 5, 15, 4],
    ], dtype=np.float32)

    scl_raster = GeoRasterGrid(scl_arr, base_10m_grid.metadata)
    zone_poly = box(73.80, 18.50, 73.84, 18.54)

    breakdown = compute_zone_scl_breakdown(scl_raster, zone_poly)

    assert breakdown.total_pixels == 16

    # Verify counts:
    # Vegetation (4): 3 pixels (at [1,0], [3,0], [3,3])
    assert breakdown.vegetation_pixels == 3
    # Soil (5): 2 pixels (at [1,1], [3,1])
    assert breakdown.bare_soil_pixels == 2
    # Water (6): 1 pixel (at [1,2])
    assert breakdown.water_pixels == 1
    # Shadow (2, 3): 2 pixels (Cast shadow [0,2] + Cloud shadow [0,3])
    assert breakdown.cloud_shadow_pixels == 2
    # Cloud (8, 9, 10): 3 pixels
    assert breakdown.cloud_pixels == 3
    # Snow (11): 1 pixel
    assert breakdown.snow_ice_pixels == 1
    # Other / Invalid (0, 1, 7, 15): 4 pixels
    assert breakdown.other_pixels == 4

    # Mutually exclusive count sum check
    total_reconstructed = (
        breakdown.vegetation_pixels +
        breakdown.bare_soil_pixels +
        breakdown.water_pixels +
        breakdown.cloud_shadow_pixels +
        breakdown.cloud_pixels +
        breakdown.snow_ice_pixels +
        breakdown.other_pixels
    )
    assert total_reconstructed == breakdown.total_pixels

    # Mutually exclusive pixel-count fraction sum check
    frac_sum = (
        breakdown.vegetation_fraction +
        breakdown.bare_soil_fraction +
        breakdown.water_fraction +
        breakdown.cloud_shadow_fraction +
        breakdown.cloud_fraction +
        breakdown.snow_ice_fraction +
        breakdown.other_fraction
    )
    assert pytest.approx(frac_sum, abs=1e-7) == 1.0

    # Area-weighted fractions sum check
    area_frac_sum = (
        breakdown.vegetation_area_fraction +
        breakdown.bare_soil_area_fraction +
        breakdown.water_area_fraction +
        breakdown.cloud_shadow_area_fraction +
        breakdown.cloud_area_fraction +
        breakdown.snow_ice_area_fraction +
        breakdown.other_area_fraction
    )
    assert pytest.approx(area_frac_sum, abs=1e-7) == 1.0


def test_scl_area_weighting_with_fractional_boundary_intersection():
    """Verify that intersection-area weighting properly accounts for fractional boundary pixels.

    Scenario:
    2 pixels along X:
    - Pixel (0, 0): Vegetation (SCL 4), extent [0.0, 0.0, 1.0, 1.0]
    - Pixel (0, 1): Bare Soil (SCL 5), extent [1.0, 0.0, 2.0, 1.0]

    Zone Polygon: box(0.0, 0.0, 1.5, 1.0)
    - Fully contains Pixel (0,0): overlap area = 1.0
    - Partially contains Pixel (0,1): overlap area = 0.5 (half pixel)

    Expected:
    - Both pixels intersect zone -> total_pixels = 2
    - Pixel-count fractions:
        vegetation_fraction = 1/2 = 0.50
        bare_soil_fraction = 1/2 = 0.50
    - Intersection-area fractions:
        total_intersected_area = 1.0 + 0.5 = 1.5
        vegetation_area_fraction = 1.0 / 1.5 = 0.6667
        bare_soil_area_fraction = 0.5 / 1.5 = 0.3333
    """
    from shapely.geometry import box
    from rasterio.transform import from_bounds
    from backend.app.intelligence.types import BoundingBox, RasterMetadata

    meta = RasterMetadata(
        scene_id="TEST_SCL_AREA",
        resolution_m=10.0,
        bounds=BoundingBox(min_x=0.0, min_y=0.0, max_x=2.0, max_y=1.0, crs="EPSG:4326"),
        rows=1,
        cols=2,
    )
    # Pixel 0 is Vegetation (4), Pixel 1 is Bare Soil (5)
    scl_data = np.array([[4, 5]], dtype=np.float32)
    scl_raster = GeoRasterGrid(scl_data, meta)

    # Zone intersects 100% of pixel 0 and 50% of pixel 1
    zone_poly = box(0.0, 0.0, 1.5, 1.0)

    breakdown = compute_zone_scl_breakdown(scl_raster, zone_poly)

    assert breakdown.total_pixels == 2
    # Pixel-count weighted: equal weight 0.50
    assert pytest.approx(breakdown.vegetation_fraction, abs=1e-4) == 0.5000
    assert pytest.approx(breakdown.bare_soil_fraction, abs=1e-4) == 0.5000

    # Area-weighted: 1.0 / 1.5 = 0.6667 and 0.5 / 1.5 = 0.3333
    assert pytest.approx(breakdown.total_intersected_area, abs=1e-4) == 1.5000
    assert pytest.approx(breakdown.vegetation_area_fraction, abs=1e-4) == 0.6667
    assert pytest.approx(breakdown.bare_soil_area_fraction, abs=1e-4) == 0.3333

    # Both sum to 1.0
    assert pytest.approx(breakdown.vegetation_fraction + breakdown.bare_soil_fraction, abs=1e-7) == 1.0
    assert pytest.approx(breakdown.vegetation_area_fraction + breakdown.bare_soil_area_fraction, abs=1e-7) == 1.0


