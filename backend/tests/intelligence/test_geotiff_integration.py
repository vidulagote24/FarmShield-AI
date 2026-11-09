"""GeoTIFF file I/O and spatial integration tests using synthetic local raster fixtures.

Tests real file I/O with rasterio:
- Writing GeoTIFF with explicit CRS, Affine transform, NoData tags.
- Reading GeoTIFF into GeoRasterGrid.
- Affine transform and coordinate georeferencing validation.
- Calculating NDVI from file bands.
- Zone polygon intersection and statistical aggregation.
- Writing derived products back to GeoTIFF.
"""

from pathlib import Path
import numpy as np
import pytest
import rasterio
from affine import Affine
from rasterio.transform import from_bounds
from shapely.geometry import box

from backend.app.intelligence.geospatial.indices import calculate_ndvi
from backend.app.intelligence.geospatial.raster_processing import GeoRasterGrid
from backend.app.intelligence.geospatial.zone_aggregation import aggregate_raster_for_zone
from backend.app.intelligence.types import SpatialQualityStatus


@pytest.fixture
def synthetic_geotiff_files(tmp_path: Path):
    """Generate temporary synthetic Red and NIR GeoTIFF files near Pune (EPSG:4326)."""
    # 20x20 pixels spanning lon [73.80, 73.82], lat [18.50, 18.52]
    # Resolution = 0.001 deg (~110 m)
    width, height = 20, 20
    minx, miny, maxx, maxy = 73.80, 18.50, 73.82, 18.52
    transform = from_bounds(minx, miny, maxx, maxy, width, height)
    crs = "EPSG:4326"

    # Red band: gradient 0.10 to 0.30
    red_data = np.linspace(0.10, 0.30, width * height, dtype=np.float32).reshape((height, width))
    # NIR band: constant 0.70 except top-left corner is NoData (-9999.0)
    nir_data = np.full((height, width), 0.70, dtype=np.float32)
    nir_data[0, 0] = -9999.0

    red_path = tmp_path / "s2_b4_red.tif"
    nir_path = tmp_path / "s2_b8_nir.tif"

    for path, data in [(red_path, red_data), (nir_path, nir_data)]:
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=1,
            dtype="float32",
            crs=crs,
            transform=transform,
            nodata=-9999.0,
        ) as dst:
            dst.write(data, 1)

    return red_path, nir_path


def test_geotiff_metadata_and_reading(synthetic_geotiff_files):
    """Verify reading GeoTIFF metadata, georeferencing, and band data."""
    red_path, nir_path = synthetic_geotiff_files

    red_grid = GeoRasterGrid.from_geotiff(str(red_path))
    assert red_grid.rows == 20
    assert red_grid.cols == 20
    assert red_grid.metadata.crs == "EPSG:4326"
    assert pytest.approx(red_grid.bounds.min_x, abs=1e-6) == 73.80
    assert pytest.approx(red_grid.bounds.max_y, abs=1e-6) == 18.52
    assert red_grid.metadata.nodata_value == -9999.0

    nir_grid = GeoRasterGrid.from_geotiff(str(nir_path))
    assert nir_grid.data[0, 0] == -9999.0
    assert pytest.approx(nir_grid.data[1, 1], abs=1e-4) == 0.70


def test_geotiff_ndvi_calculation_and_zonal_aggregation(synthetic_geotiff_files):
    """Verify calculating NDVI from GeoTIFF inputs and aggregating across a zone."""
    red_path, nir_path = synthetic_geotiff_files

    red_grid = GeoRasterGrid.from_geotiff(str(red_path))
    nir_grid = GeoRasterGrid.from_geotiff(str(nir_path))

    # Mask NoData pixel in NIR
    nir_clean = np.where(nir_grid.data == -9999.0, np.nan, nir_grid.data)
    ndvi_array = calculate_ndvi(red_grid.data, nir_clean)

    ndvi_grid = GeoRasterGrid(ndvi_array, nir_grid.metadata)

    # Zone spanning 10x10 pixels in the center of the GeoTIFF
    # [73.805, 18.505, 73.815, 18.515]
    zone_poly = box(73.805, 18.505, 73.815, 18.515)

    stats = aggregate_raster_for_zone(
        zone_geom=zone_poly,
        raster=ndvi_grid,
        zone_id="ZONE_GEOTIFF_01",
    )

    assert stats.zone_id == "ZONE_GEOTIFF_01"
    assert stats.quality_status == SpatialQualityStatus.GOOD
    assert stats.total_pixels_in_geometry > 0
    assert stats.valid_pixel_fraction == 1.0
    # Expected NDVI: Red is ~0.20, NIR is 0.70 -> (0.7 - 0.2) / (0.7 + 0.2) = 0.5 / 0.9 ~= 0.5556
    assert 0.50 < stats.mean < 0.65


def test_write_derived_geotiff_and_reopen(synthetic_geotiff_files, tmp_path: Path):
    """Verify writing a computed GeoRasterGrid back to GeoTIFF and reading it with rasterio."""
    red_path, nir_path = synthetic_geotiff_files
    nir_grid = GeoRasterGrid.from_geotiff(str(nir_path))

    output_path = tmp_path / "output_ndvi.tif"
    nir_grid.to_geotiff(str(output_path))

    assert output_path.exists()

    with rasterio.open(output_path) as dst:
        assert dst.count == 1
        assert dst.height == 20
        assert dst.width == 20
        assert dst.crs.to_string() == "EPSG:4326"
        assert dst.nodata == -9999.0
        reopened_data = dst.read(1)
        assert pytest.approx(reopened_data[1, 1], abs=1e-4) == 0.70


def test_rotated_geotiff_rejection(tmp_path: Path):
    """Verify that a rotated/skewed GeoTIFF is explicitly validated and rejected."""
    # Affine with 15-degree rotation -> non-zero b and d
    rotated_transform = Affine.translation(73.80, 18.50) @ Affine.rotation(15.0) @ Affine.scale(0.001, -0.001)

    rotated_path = tmp_path / "rotated_scene.tif"
    data = np.ones((10, 10), dtype=np.float32)

    with rasterio.open(
        rotated_path,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=rotated_transform,
    ) as dst:
        dst.write(data, 1)

    with pytest.raises(ValueError, match="Unsupported rotated or sheared raster"):
        GeoRasterGrid.from_geotiff(str(rotated_path))

