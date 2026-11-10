"""Tests for spatial quality assessment and configurable coverage thresholds."""

import numpy as np
import pytest
from shapely.geometry import box

from backend.app.intelligence.config import GeospatialConfig
from backend.app.intelligence.geospatial.quality import assess_spatial_quality
from backend.app.intelligence.geospatial.raster_processing import GeoRasterGrid
from backend.app.intelligence.geospatial.zone_aggregation import aggregate_raster_for_zone
from backend.app.intelligence.types import BoundingBox, RasterMetadata, SpatialQualityStatus


def test_assess_spatial_quality_logic():
    """Verify assess_spatial_quality function behavior across edge cases."""
    # 1. Zero total pixels -> NO_SPATIAL_OVERLAP
    status, note = assess_spatial_quality(total_pixels=0, valid_pixels=0, valid_fraction=0.0)
    assert status == SpatialQualityStatus.NO_SPATIAL_OVERLAP

    # 2. Zero valid pixels -> INSUFFICIENT_COVERAGE
    status, note = assess_spatial_quality(total_pixels=20, valid_pixels=0, valid_fraction=0.0, has_cloud_contamination=True)
    assert status == SpatialQualityStatus.INSUFFICIENT_COVERAGE
    assert "cloud" in note.lower()

    # 3. Valid pixels below minimum count threshold (e.g. 2 < 3)
    status, note = assess_spatial_quality(total_pixels=2, valid_pixels=2, valid_fraction=1.0, min_pixel_count_threshold=3)
    assert status == SpatialQualityStatus.INSUFFICIENT_COVERAGE
    assert "below absolute minimum" in note

    # 4. Valid fraction below configurable threshold (e.g. 50% < 60%)
    status, note = assess_spatial_quality(
        total_pixels=100,
        valid_pixels=50,
        valid_fraction=0.50,
        min_valid_fraction_threshold=0.60,
        has_cloud_contamination=True,
    )
    assert status == SpatialQualityStatus.CLOUD_CONTAMINATED
    assert "below configured threshold (60.0%)" in note

    # 5. Sufficient coverage -> GOOD
    status, note = assess_spatial_quality(
        total_pixels=100,
        valid_pixels=85,
        valid_fraction=0.85,
        min_valid_fraction_threshold=0.60,
    )
    assert status == SpatialQualityStatus.GOOD
    assert note is None


def test_configurable_threshold_withholding_in_aggregation():
    """Verify that aggregate_raster_for_zone respects configurable threshold and records it.

    Suppose a zone has 50% valid pixels and 50% cloud-masked pixels:
    - When threshold is 0.40: Quality is GOOD, statistics are returned.
    - When threshold is 0.60: Quality is CLOUD_CONTAMINATED, statistics are withheld (None).
    """
    bounds = BoundingBox(min_x=73.80, min_y=18.50, max_x=73.90, max_y=18.60, crs="EPSG:4326")
    meta = RasterMetadata(
        scene_id="S2A_TEST_CONFIGURABLE",
        crs="EPSG:4326",
        resolution_m=10.0,
        bounds=bounds,
        rows=10,
        cols=10,
    )
    data = np.full((10, 10), 0.70, dtype=np.float32)
    raster = GeoRasterGrid(data, meta)

    # 10x10 mask where right half is cloudy
    valid_mask = np.ones((10, 10), dtype=bool)
    valid_mask[:, 5:] = False  # 50% cloudy

    # Zone spanning the whole grid
    zone_poly = box(73.80, 18.50, 73.90, 18.60)

    # Run with lenient threshold 0.40
    lenient_config = GeospatialConfig(min_valid_pixel_fraction=0.40)
    stats_lenient = aggregate_raster_for_zone(
        zone_geom=zone_poly,
        raster=raster,
        valid_mask=valid_mask,
        config=lenient_config,
    )
    assert stats_lenient.min_valid_fraction_threshold == 0.40
    assert stats_lenient.quality_status == SpatialQualityStatus.GOOD
    assert stats_lenient.mean == 0.70

    # Run with standard provisional threshold 0.60
    strict_config = GeospatialConfig(min_valid_pixel_fraction=0.60)
    stats_strict = aggregate_raster_for_zone(
        zone_geom=zone_poly,
        raster=raster,
        valid_mask=valid_mask,
        config=strict_config,
    )
    assert stats_strict.min_valid_fraction_threshold == 0.60
    assert stats_strict.quality_status == SpatialQualityStatus.CLOUD_CONTAMINATED
    # Statistics must be withheld to avoid misleading decisions
    assert stats_strict.mean is None
    assert stats_strict.median is None
    assert "below configured threshold (60.0%)" in stats_strict.quality_note


def test_threshold_boundary_exactly_equal():
    """Verify that a valid pixel fraction exactly equal to threshold is accepted (boundary test)."""
    # 60 valid out of 100 total -> valid_fraction == 0.60
    status, note = assess_spatial_quality(
        total_pixels=100,
        valid_pixels=60,
        valid_fraction=0.60,
        min_valid_fraction_threshold=0.60,
        has_cloud_contamination=True,
    )
    assert status == SpatialQualityStatus.GOOD
    assert note is None


def test_threshold_boundary_immediately_below():
    """Verify that a valid pixel fraction immediately below threshold is rejected (boundary test)."""
    # 59 valid out of 100 total -> valid_fraction == 0.59 (< 0.60)
    status, note = assess_spatial_quality(
        total_pixels=100,
        valid_pixels=59,
        valid_fraction=0.59,
        min_valid_fraction_threshold=0.60,
        has_cloud_contamination=True,
    )
    assert status == SpatialQualityStatus.CLOUD_CONTAMINATED
    assert "below configured threshold" in note


def test_insufficient_valid_pixel_count_boundary():
    """Verify that even with 100% fraction, having fewer valid pixels than min_pixel_count fails."""
    # 2 valid out of 2 total -> fraction 1.0, but count 2 < min_pixel_count (3)
    status, note = assess_spatial_quality(
        total_pixels=2,
        valid_pixels=2,
        valid_fraction=1.0,
        min_valid_fraction_threshold=0.60,
        min_pixel_count_threshold=3,
    )
    assert status == SpatialQualityStatus.INSUFFICIENT_COVERAGE
    assert "below absolute minimum" in note

