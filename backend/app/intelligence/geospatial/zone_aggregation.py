"""Zone-level raster statistical aggregation with quality screening.

Intersects management zone vector polygons with georeferenced raster arrays,
extracts intersecting pixels, computes robust summary statistics (mean, median,
min, max, std), and assesses spatial coverage quality against configurable thresholds.
"""

from typing import List, Optional, Union
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, box

from backend.app.intelligence.config import GeospatialConfig, default_geospatial_config
from backend.app.intelligence.geospatial.geometry import validate_polygon_geometry
from backend.app.intelligence.geospatial.quality import assess_spatial_quality
from backend.app.intelligence.geospatial.raster_processing import GeoRasterGrid
from backend.app.intelligence.types import SpatialQualityStatus, ZoneRasterStats


def aggregate_raster_for_zone(
    zone_geom: Union[Polygon, MultiPolygon],
    raster: GeoRasterGrid,
    valid_mask: Optional[np.ndarray] = None,
    index_name: str = "NDVI",
    zone_id: Optional[str] = None,
    config: Optional[GeospatialConfig] = None,
) -> ZoneRasterStats:
    """Aggregate raster cell values across a management zone geometry.

    Follows strict integrity rules:
    - Never fabricates statistics if valid pixel count is insufficient.
    - Accurately tracks total intersecting pixels vs unmasked valid pixels.
    - Records the applied minimum valid-pixel fraction threshold in the returned result.

    Args:
        zone_geom: Shapely Polygon or MultiPolygon in EPSG:4326.
        raster: GeoRasterGrid containing georeferenced 2D float array.
        valid_mask: Optional 2D boolean array (True = clear, False = cloudy/NoData).
                   If None, all non-NaN, non-NoData pixels are treated as valid.
        index_name: Name of the index or variable (e.g. 'NDVI').
        zone_id: Optional identifier for the zone.
        config: Optional GeospatialConfig overriding default thresholds.

    Returns:
        ZoneRasterStats containing statistics, pixel counts, coverage fraction, and quality status.
    """
    cfg = config or default_geospatial_config
    threshold = cfg.min_valid_pixel_fraction

    # 1. Validate zone geometry
    geom_val = validate_polygon_geometry(zone_geom)
    if not geom_val.is_valid:
        return ZoneRasterStats(
            zone_id=zone_id,
            index_name=index_name,
            total_pixels_in_geometry=0,
            valid_pixel_count=0,
            valid_pixel_fraction=0.0,
            min_valid_fraction_threshold=threshold,
            quality_status=SpatialQualityStatus.INVALID_GEOMETRY,
            quality_note=f"Invalid geometry: {geom_val.error_message}",
        )

    # 2. Check spatial bounding box overlap with raster
    z_minx, z_miny, z_maxx, z_maxy = zone_geom.bounds
    r_bounds = raster.bounds

    if (z_maxx < r_bounds.min_x or z_minx > r_bounds.max_x or
            z_maxy < r_bounds.min_y or z_miny > r_bounds.max_y):
        return ZoneRasterStats(
            zone_id=zone_id,
            index_name=index_name,
            total_pixels_in_geometry=0,
            valid_pixel_count=0,
            valid_pixel_fraction=0.0,
            min_valid_fraction_threshold=threshold,
            quality_status=SpatialQualityStatus.NO_SPATIAL_OVERLAP,
            quality_note="Zone does not intersect raster bounding box.",
        )

    # 3. Determine candidate pixel indices window
    col_min = max(0, int(np.floor((z_minx - r_bounds.min_x) / raster.pixel_width)))
    col_max = min(raster.cols - 1, int(np.ceil((z_maxx - r_bounds.min_x) / raster.pixel_width)))
    row_min = max(0, int(np.floor((r_bounds.max_y - z_maxy) / raster.pixel_height)))
    row_max = min(raster.rows - 1, int(np.ceil((r_bounds.max_y - z_miny) / raster.pixel_height)))

    if col_min > col_max or row_min > row_max:
        return ZoneRasterStats(
            zone_id=zone_id,
            index_name=index_name,
            total_pixels_in_geometry=0,
            valid_pixel_count=0,
            valid_pixel_fraction=0.0,
            min_valid_fraction_threshold=threshold,
            quality_status=SpatialQualityStatus.NO_SPATIAL_OVERLAP,
            quality_note="Zone window falls outside raster coordinates.",
        )

    # 4. Sample pixels inside candidate window
    total_pixels_in_geometry = 0
    valid_values: List[float] = []
    masked_due_to_cloud_or_nodata = False

    # Default valid mask if none provided
    if valid_mask is None:
        grid_valid = np.isfinite(raster.data)
        if raster.metadata.nodata_value is not None:
            grid_valid = grid_valid & (raster.data != raster.metadata.nodata_value)
    else:
        grid_valid = valid_mask

    # Calculate pixel area in squared CRS coordinate units using the full 2D affine
    # transformation determinant |a * e - b * d| via raster.pixel_area.
    #
    # CRS Units and Overlap Fraction Distinction:
    # - In EPSG:4326 (WGS84), pixel_area is in square degrees (deg^2), NOT square metres.
    # - In projected CRS (e.g., UTM), pixel_area is in square metres (m^2).
    # - For zone filtering, overlap.area / pixel_area is a strictly DIMENSIONLESS fraction
    #   (deg^2 / deg^2 or m^2 / m^2), representing the geometric proportion of the pixel
    #   contained within the zone boundary.
    # - This dimensionless ratio is compared against cfg.min_pixel_overlap_fraction
    #   via: overlap.area > pixel_area * cfg.min_pixel_overlap_fraction.
    # - This is purely a geometric pixel-selection criterion; it is NOT a physical ground area calculation.
    # - Physical ground area of zones MUST be computed using geodesic methods
    #   (e.g., calculate_geodesic_area_m2) or properly projected equal-area CRS.
    # - Zonal aggregation assumes north-up, axis-aligned rasters so that candidate
    #   pixels can be indexed rectangularly and bounded by axis-aligned bounding boxes.
    pixel_area = raster.pixel_area
    min_overlap_area = pixel_area * cfg.min_pixel_overlap_fraction

    for r in range(row_min, row_max + 1):
        for c in range(col_min, col_max + 1):
            p_minx, p_miny, p_maxx, p_maxy = raster.get_pixel_bounds(r, c)
            pixel_polygon = box(p_minx, p_miny, p_maxx, p_maxy)

            # Check if pixel has genuine 2D spatial overlap with zone geometry
            # Uses scale-invariant threshold to handle both geographic (degrees)
            # and projected (meters) coordinate reference systems accurately.
            if pixel_polygon.intersects(zone_geom):
                overlap = pixel_polygon.intersection(zone_geom)
                if not overlap.is_empty and overlap.area > min_overlap_area:
                    total_pixels_in_geometry += 1
                    val = raster.data[r, c]

                    if grid_valid[r, c] and np.isfinite(val):
                        valid_values.append(float(val))
                    else:
                        masked_due_to_cloud_or_nodata = True

    valid_pixel_count = len(valid_values)
    valid_fraction = (
        (valid_pixel_count / total_pixels_in_geometry)
        if total_pixels_in_geometry > 0 else 0.0
    )

    # 5. Evaluate spatial quality status
    quality_status, quality_note = assess_spatial_quality(
        total_pixels=total_pixels_in_geometry,
        valid_pixels=valid_pixel_count,
        valid_fraction=valid_fraction,
        min_valid_fraction_threshold=threshold,
        min_pixel_count_threshold=cfg.min_pixel_count,
        has_cloud_contamination=masked_due_to_cloud_or_nodata,
    )

    # 6. Calculate statistics only if quality is acceptable and sufficient pixels exist
    if quality_status == SpatialQualityStatus.GOOD and valid_pixel_count >= cfg.min_pixel_count:
        arr = np.array(valid_values, dtype=np.float64)
        mean_val = float(np.mean(arr))
        median_val = float(np.median(arr))
        min_val = float(np.min(arr))
        max_val = float(np.max(arr))
        std_val = float(np.std(arr))
    else:
        # Honest representation: withhold statistical metrics when data is insufficient
        mean_val = None
        median_val = None
        min_val = None
        max_val = None
        std_val = None

    return ZoneRasterStats(
        zone_id=zone_id,
        index_name=index_name,
        mean=round(mean_val, 4) if mean_val is not None else None,
        median=round(median_val, 4) if median_val is not None else None,
        min=round(min_val, 4) if min_val is not None else None,
        max=round(max_val, 4) if max_val is not None else None,
        std=round(std_val, 4) if std_val is not None else None,
        total_pixels_in_geometry=total_pixels_in_geometry,
        valid_pixel_count=valid_pixel_count,
        valid_pixel_fraction=round(valid_fraction, 4),
        min_valid_fraction_threshold=threshold,
        quality_status=quality_status,
        quality_note=quality_note,
    )

