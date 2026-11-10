"""Tests for zonal raster aggregation across management zones."""

import numpy as np
import pytest
from shapely.geometry import Polygon, box

from backend.app.intelligence.config import GeospatialConfig
from backend.app.intelligence.geospatial.raster_processing import GeoRasterGrid
from backend.app.intelligence.geospatial.zone_aggregation import aggregate_raster_for_zone
from backend.app.intelligence.types import BoundingBox, RasterMetadata, SpatialQualityStatus


@pytest.fixture
def sample_raster():
    """Create a 10x10 synthetic raster with known pixel values and bounds."""
    bounds = BoundingBox(min_x=73.80, min_y=18.50, max_x=73.90, max_y=18.60, crs="EPSG:4326")
    meta = RasterMetadata(
        scene_id="S2A_TEST_SYNTHETIC",
        crs="EPSG:4326",
        resolution_m=10.0,
        bounds=bounds,
        rows=10,
        cols=10,
        nodata_value=-9999.0,
    )
    # Create grid with gradient values
    data = np.arange(100, dtype=np.float32).reshape((10, 10)) / 100.0  # 0.00 to 0.99
    return GeoRasterGrid(data, meta)


def test_zone_aggregation_perfect_coverage(sample_raster):
    """Verify statistical aggregation when all zone pixels are valid and clear."""
    # A box matching exactly 2x2 pixels inside the grid
    # Lon: [73.82, 73.84], Lat: [18.52, 18.54]
    # Width = 0.02 deg = 2 pixels, Height = 0.02 deg = 2 pixels
    zone_poly = box(73.82, 18.52, 73.84, 18.54)

    stats = aggregate_raster_for_zone(
        zone_geom=zone_poly,
        raster=sample_raster,
        zone_id="ZONE_01",
    )

    assert stats.zone_id == "ZONE_01"
    assert stats.quality_status == SpatialQualityStatus.GOOD
    assert stats.total_pixels_in_geometry > 0
    assert stats.valid_pixel_count == stats.total_pixels_in_geometry
    assert stats.valid_pixel_fraction == 1.0
    assert stats.mean is not None
    assert stats.median is not None
    assert stats.min is not None
    assert stats.max is not None
    assert stats.min <= stats.median <= stats.max


def test_zone_aggregation_disjoint_geometry(sample_raster):
    """Verify handling when zone is completely outside raster bounding box."""
    far_zone = box(74.50, 19.50, 74.60, 19.60)

    stats = aggregate_raster_for_zone(
        zone_geom=far_zone,
        raster=sample_raster,
        zone_id="ZONE_DISJOINT",
    )

    assert stats.quality_status == SpatialQualityStatus.NO_SPATIAL_OVERLAP
    assert stats.total_pixels_in_geometry == 0
    assert stats.valid_pixel_count == 0
    assert stats.valid_pixel_fraction == 0.0
    assert stats.mean is None
    assert stats.median is None


def test_zone_aggregation_invalid_geometry(sample_raster):
    """Verify handling when zone geometry is topologically invalid."""
    bowtie = Polygon([
        (73.82, 18.52), (73.84, 18.54),
        (73.82, 18.54), (73.84, 18.52),
        (73.82, 18.52),
    ])

    stats = aggregate_raster_for_zone(
        zone_geom=bowtie,
        raster=sample_raster,
        zone_id="ZONE_INVALID",
    )

    assert stats.quality_status == SpatialQualityStatus.INVALID_GEOMETRY
    assert stats.mean is None
    assert "Invalid geometry" in stats.quality_note


def test_zone_aggregation_polygon_with_hole(sample_raster):
    """Verify that pixels falling inside an interior hole are excluded from zonal statistics."""
    # Outer box: 4x4 pixels (73.81 to 73.85, 18.51 to 18.55) -> 16 pixels
    outer = box(73.81, 18.51, 73.85, 18.55)
    # Inner hole: 2x2 pixels in the center (73.82 to 73.84, 18.52 to 18.54) -> 4 pixels
    inner = box(73.82, 18.52, 73.84, 18.54)

    donut_poly = Polygon(outer.exterior.coords, [inner.exterior.coords])

    stats = aggregate_raster_for_zone(
        zone_geom=donut_poly,
        raster=sample_raster,
        zone_id="ZONE_DONUT",
    )

    assert stats.quality_status == SpatialQualityStatus.GOOD
    # Total pixels must be outer (16) minus inner (4) = 12 pixels
    assert stats.total_pixels_in_geometry == 12
    assert stats.valid_pixel_count == 12
    assert stats.valid_pixel_fraction == 1.0
    assert stats.mean is not None

