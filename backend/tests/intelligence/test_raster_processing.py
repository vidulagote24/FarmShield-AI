"""Tests for GeoRasterGrid georeferencing, NoData masking, and cloud quality filtering."""

from datetime import datetime
import numpy as np
import pytest

from backend.app.intelligence.geospatial.raster_processing import GeoRasterGrid, create_valid_mask
from backend.app.intelligence.types import BoundingBox, RasterMetadata


def test_georaster_grid_coordinate_conversions():
    """Verify that continuous spatial coordinates map accurately to discrete grid pixels."""
    # 10x10 grid covering (73.80 to 73.90 lon, 18.50 to 18.60 lat)
    bounds = BoundingBox(min_x=73.80, min_y=18.50, max_x=73.90, max_y=18.60, crs="EPSG:4326")
    meta = RasterMetadata(
        scene_id="S2A_TEST_001",
        acquisition_time=datetime(2026, 11, 7, 5, 30, 0),
        crs="EPSG:4326",
        resolution_m=10.0,
        bounds=bounds,
        rows=10,
        cols=10,
        nodata_value=-9999.0,
    )
    arr = np.ones((10, 10), dtype=np.float32)
    raster = GeoRasterGrid(arr, meta)

    # Pixel width and height must each be (0.10 / 10) = 0.01 deg
    assert pytest.approx(raster.pixel_width, abs=1e-6) == 0.01
    assert pytest.approx(raster.pixel_height, abs=1e-6) == 0.01

    # Top-left corner (73.805, 18.595) should map to row 0, col 0
    row, col = raster.coord_to_pixel(73.805, 18.595)
    assert row == 0 and col == 0

    # Bottom-right corner (73.895, 18.505) should map to row 9, col 9
    row, col = raster.coord_to_pixel(73.895, 18.505)
    assert row == 9 and col == 9

    # Reverse: pixel (0, 0) center should be (73.805, 18.595)
    x, y = raster.pixel_to_coord(0, 0)
    assert pytest.approx(x, abs=1e-6) == 73.805
    assert pytest.approx(y, abs=1e-6) == 18.595


def test_create_valid_mask_with_nodata_and_clouds():
    """Verify combination of NoData, NaN, and cloud boolean masks."""
    data = np.array([
        [0.5, -9999.0],
        [np.nan, 0.7],
    ], dtype=np.float32)

    # Cloud mask: True = clear, False = cloud
    cloud_mask = np.array([
        [True, True],
        [True, False],  # Pixel (1, 1) is cloudy
    ], dtype=bool)

    valid = create_valid_mask(data, nodata_value=-9999.0, cloud_mask=cloud_mask)

    # Only pixel (0, 0) is valid: non-NaN, not -9999, not cloudy
    assert valid[0, 0] == True
    assert valid[0, 1] == False  # NoData
    assert valid[1, 0] == False  # NaN
    assert valid[1, 1] == False  # Cloudy


def test_create_valid_mask_with_sentinel2_scl():
    """Verify masking according to Copernicus Sentinel-2 SCL classification.

    Tests both:
    1. Default vegetation mode (vegetation_only=True): Strictly isolates Class 4 (general green vegetation);
       bare soil (Class 5) and water (Class 6) are excluded.
    2. Clear surface observation mode (vegetation_only=False): Accepts classes {4, 5, 6}.
    """
    data = np.full((1, 4), 0.5, dtype=np.float32)
    # SCL codes: 4 = vegetation, 5 = bare soil, 8 = cloud medium, 3 = shadow
    scl = np.array([[4, 5, 8, 3]], dtype=np.uint8)

    # 1. Default vegetation mode: bare soil (5) is excluded from vegetation statistics
    valid_veg = create_valid_mask(data, scl_layer=scl, vegetation_only=True)
    assert valid_veg[0, 0] == True   # Vegetation (4)
    assert valid_veg[0, 1] == False  # Bare soil (5) excluded
    assert valid_veg[0, 2] == False  # Cloud (8)
    assert valid_veg[0, 3] == False  # Shadow (3)

    # Backward compatibility parameter check
    valid_crop_compat = create_valid_mask(data, scl_layer=scl, crop_vegetation_only=True)
    assert np.array_equal(valid_veg, valid_crop_compat)

    # 2. Clear surface observation mode: bare soil (5) is accepted as clear sky observation
    valid_clear = create_valid_mask(data, scl_layer=scl, vegetation_only=False)
    assert valid_clear[0, 0] == True   # Vegetation (4)
    assert valid_clear[0, 1] == True   # Bare soil (5)
    assert valid_clear[0, 2] == False  # Cloud (8)
    assert valid_clear[0, 3] == False  # Shadow (3)


def test_pixel_area_affine_determinant():
    """Verify pixel_area calculation uses the full affine transformation determinant |a * e - b * d|."""
    bounds = BoundingBox(min_x=73.80, min_y=18.50, max_x=73.84, max_y=18.54, crs="EPSG:4326")
    meta = RasterMetadata(
        scene_id="TEST_GRID",
        crs="EPSG:4326",
        resolution_m=10.0,
        bounds=bounds,
        rows=4,
        cols=4,
    )
    grid = GeoRasterGrid(np.zeros((4, 4), dtype=np.float32), meta)

    t = grid.transform
    # For Affine transform: determinant = a * e - b * d
    expected_det_area = abs(t.a * t.e - t.b * t.d)
    assert grid.pixel_area == expected_det_area
    assert pytest.approx(grid.pixel_area, abs=1e-9) == grid.pixel_width * grid.pixel_height

    # Validate rectilinear grid succeeds axis-aligned check
    grid.validate_axis_aligned()


def test_pixel_area_crs_units_and_dimensionless_overlap():
    """Verify that pixel_area is strictly in squared CRS units and overlap check is dimensionless."""
    # 1. Geographic CRS (EPSG:4326): pixel_area is in square degrees, NOT square metres
    wgs84_bounds = BoundingBox(min_x=73.80, min_y=18.50, max_x=73.84, max_y=18.54, crs="EPSG:4326")
    meta_wgs84 = RasterMetadata(
        scene_id="TEST_WGS84",
        crs="EPSG:4326",
        resolution_m=1110.0,
        bounds=wgs84_bounds,
        rows=4,
        cols=4,
    )
    grid_wgs84 = GeoRasterGrid(np.zeros((4, 4), dtype=np.float32), meta_wgs84)

    # Pixel width and height are in degrees: 0.04 / 4 = 0.01 deg
    assert pytest.approx(grid_wgs84.pixel_width, abs=1e-6) == 0.01
    assert pytest.approx(grid_wgs84.pixel_height, abs=1e-6) == 0.01
    # pixel_area is strictly in deg^2 (0.01 * 0.01 = 0.0001 deg^2)
    assert pytest.approx(grid_wgs84.pixel_area, abs=1e-9) == 0.0001
    assert grid_wgs84.metadata.crs == "EPSG:4326"

    # 2. Projected CRS (UTM in meters, EPSG:32643): pixel_area is in square metres (m^2)
    utm_bounds = BoundingBox(min_x=373000.0, min_y=2045000.0, max_x=373040.0, max_y=2045040.0, crs="EPSG:32643")
    meta_utm = RasterMetadata(
        scene_id="TEST_UTM",
        crs="EPSG:32643",
        resolution_m=10.0,
        bounds=utm_bounds,
        rows=4,
        cols=4,
    )
    grid_utm = GeoRasterGrid(np.zeros((4, 4), dtype=np.float32), meta_utm)

    # Pixel width and height are in metres: 40.0 / 4 = 10.0 m
    assert pytest.approx(grid_utm.pixel_width, abs=1e-6) == 10.0
    assert pytest.approx(grid_utm.pixel_height, abs=1e-6) == 10.0
    # pixel_area is strictly in m^2 (10.0 * 10.0 = 100.0 m^2)
    assert pytest.approx(grid_utm.pixel_area, abs=1e-6) == 100.0

