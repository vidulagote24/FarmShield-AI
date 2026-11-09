"""Polygon geometry validation, geodesic area calculation, and CRS operations.

Strict scientific principles enforced:
1. Never calculate area directly in geographic degrees.
2. Use ellipsoidal geodesic calculations (WGS84) for surface area.
3. Validate geometry topology (closure, self-intersection, emptiness).
4. Preserve CRS metadata and provide explicit transformations.
"""

from typing import Any, Dict, Optional, Tuple, Union
import numpy as np
import pyproj
from pyproj import CRS, Geod, Transformer
import shapely
from shapely.geometry import Polygon, MultiPolygon, shape
import shapely.ops

from backend.app.intelligence.types import BoundingBox, GeometryValidationResult


# Standard WGS84 Geod instance for ellipsoidal area calculations
_WGS84_GEOD = Geod(ellps="WGS84")


def _single_polygon_geodesic_area_m2(poly: Polygon) -> float:
    """Calculate geodesic area of a single polygon, explicitly subtracting interior holes.

    Pyproj's geometry_area_perimeter sums signed areas based on ring winding order.
    To avoid winding-order discrepancies where holes might inadvertently add area,
    we explicitly compute the positive exterior ring area and subtract each positive
    interior ring (hole) area.
    """
    if poly.is_empty:
        return 0.0
    ext_area, _ = _WGS84_GEOD.geometry_area_perimeter(Polygon(poly.exterior))
    net_area = abs(float(ext_area))
    for interior in poly.interiors:
        hole_area, _ = _WGS84_GEOD.geometry_area_perimeter(Polygon(interior))
        net_area -= abs(float(hole_area))
    return max(0.0, net_area)


def calculate_geodesic_area_m2(geom: Union[Polygon, MultiPolygon]) -> float:
    """Calculate the geodesic ellipsoidal area in square meters for WGS84 coordinates.

    Properly handles both single Polygons (including interior holes) and MultiPolygons.

    Args:
        geom: A Shapely Polygon or MultiPolygon with coordinates in (longitude, latitude) EPSG:4326.

    Returns:
        Surface area in square meters. Returns 0.0 for empty geometry.

    Raises:
        ValueError: If geometry is not a Polygon or MultiPolygon.
    """
    if geom.is_empty:
        return 0.0

    if isinstance(geom, Polygon):
        return _single_polygon_geodesic_area_m2(geom)
    elif isinstance(geom, MultiPolygon):
        return sum(_single_polygon_geodesic_area_m2(part) for part in geom.geoms)
    else:
        raise ValueError(f"Geometry must be Polygon or MultiPolygon, got {geom.geom_type}")


def calculate_geodesic_area_ha(geom: Union[Polygon, MultiPolygon]) -> float:
    """Calculate the geodesic area in hectares (1 ha = 10,000 m²).

    Args:
        geom: A Shapely Polygon or MultiPolygon in EPSG:4326.

    Returns:
        Surface area in hectares.
    """
    area_m2 = calculate_geodesic_area_m2(geom)
    return area_m2 / 10000.0


def validate_polygon_geometry(
    geometry_input: Union[Dict[str, Any], Polygon, MultiPolygon],
    crs_str: str = "EPSG:4326",
) -> GeometryValidationResult:
    """Validate a polygon geometry, checking topological validity and computing geodesic bounds/area.

    Args:
        geometry_input: GeoJSON geometry dict or Shapely Polygon/MultiPolygon.
        crs_str: Coordinate reference system of input coordinates (default EPSG:4326).

    Returns:
        GeometryValidationResult with validity flags, error message if any, and calculated area.
    """
    # 1. Parse into Shapely object
    try:
        if isinstance(geometry_input, dict):
            geom = shape(geometry_input)
        elif isinstance(geometry_input, (Polygon, MultiPolygon)):
            geom = geometry_input
        else:
            return GeometryValidationResult(
                is_valid=False,
                error_message=f"Unsupported geometry type: {type(geometry_input).__name__}",
                is_empty=True,
            )
    except Exception as exc:
        return GeometryValidationResult(
            is_valid=False,
            error_message=f"Failed to parse geometry: {str(exc)}",
            is_empty=True,
        )

    # 2. Check empty
    if geom.is_empty:
        return GeometryValidationResult(
            is_valid=False,
            error_message="Geometry is empty (contains no coordinates)",
            is_empty=True,
            geometry_type=geom.geom_type,
        )

    # 3. Check topology validity (e.g. self-intersections)
    if not geom.is_valid:
        reason = shapely.is_valid_reason(geom)
        return GeometryValidationResult(
            is_valid=False,
            error_message=f"Invalid geometry topology: {reason}",
            is_empty=False,
            geometry_type=geom.geom_type,
        )

    # 4. Enforce Polygon or MultiPolygon
    if not isinstance(geom, (Polygon, MultiPolygon)):
        return GeometryValidationResult(
            is_valid=False,
            error_message=f"Expected Polygon or MultiPolygon, received {geom.geom_type}",
            is_empty=False,
            geometry_type=geom.geom_type,
        )

    # 5. Coordinate sanity checks for EPSG:4326
    minx, miny, maxx, maxy = geom.bounds
    if crs_str.upper() in ("EPSG:4326", "WGS84"):
        if minx < -180.0 or maxx > 180.0 or miny < -90.0 or maxy > 90.0:
            return GeometryValidationResult(
                is_valid=False,
                error_message=(
                    f"Coordinates out of WGS84 bounds: lon [{minx}, {maxx}] must be [-180, 180], "
                    f"lat [{miny}, {maxy}] must be [-90, 90]"
                ),
                is_empty=False,
                geometry_type=geom.geom_type,
            )

    # 6. Calculate true geodesic area (m² and ha)
    try:
        area_m2 = calculate_geodesic_area_m2(geom)
        area_ha = area_m2 / 10000.0
    except Exception as exc:
        return GeometryValidationResult(
            is_valid=False,
            error_message=f"Geodesic area calculation failed: {str(exc)}",
            is_empty=False,
            geometry_type=geom.geom_type,
        )

    # 7. Check for degenerate geometry (e.g. collapsed collinear points with zero area)
    if area_m2 <= 1e-4:
        return GeometryValidationResult(
            is_valid=False,
            error_message="Degenerate polygon with zero or negligible area",
            is_empty=False,
            geometry_type=geom.geom_type,
        )

    bounds = BoundingBox(
        min_x=minx,
        min_y=miny,
        max_x=maxx,
        max_y=maxy,
        crs=crs_str,
    )

    return GeometryValidationResult(
        is_valid=True,
        error_message=None,
        is_empty=False,
        geometry_type=geom.geom_type,
        area_m2=round(area_m2, 2),
        area_ha=round(area_ha, 4),
        bounds=bounds,
    )


def check_zone_contained_in_farm(
    farm_geom: Union[Polygon, MultiPolygon],
    zone_geom: Union[Polygon, MultiPolygon],
    tolerance_m2: float = 1.0,
) -> Tuple[bool, float]:
    """Verify that a zone geometry lies strictly within its parent farm boundary.

    Args:
        farm_geom: Farm boundary Polygon or MultiPolygon in EPSG:4326.
        zone_geom: Zone boundary Polygon or MultiPolygon in EPSG:4326.
        tolerance_m2: Allowed external area in square meters to tolerate boundary snapping jitter.

    Returns:
        Tuple of (is_contained: bool, outside_area_m2: float).
    """
    if not farm_geom.is_valid or not zone_geom.is_valid:
        raise ValueError("Both farm and zone geometries must be valid to check containment.")

    # Difference: area of zone that lies outside farm
    outside_geom = zone_geom.difference(farm_geom)
    if outside_geom.is_empty:
        return True, 0.0

    outside_area_m2 = calculate_geodesic_area_m2(outside_geom)
    is_contained = outside_area_m2 <= tolerance_m2
    return is_contained, outside_area_m2


def transform_geometry_crs(
    geom: Union[Polygon, MultiPolygon],
    src_crs: str,
    target_crs: str,
) -> Union[Polygon, MultiPolygon]:
    """Transform geometry coordinates between coordinate reference systems.

    Args:
        geom: Shapely Polygon or MultiPolygon.
        src_crs: Source CRS identifier (e.g. 'EPSG:4326').
        target_crs: Target CRS identifier (e.g. 'EPSG:32643').

    Returns:
        Transformed Shapely geometry in target CRS.
    """
    if src_crs.upper() == target_crs.upper():
        return geom

    transformer = Transformer.from_crs(src_crs, target_crs, always_xy=True)
    transformed_geom = shapely.transform(
        geom,
        lambda coords: np.column_stack(transformer.transform(coords[:, 0], coords[:, 1]))
    )
    return transformed_geom
