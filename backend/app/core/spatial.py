"""Geospatial validation, area calculation, and GeoJSON serialization utilities."""

import json
import math
from typing import Any, Dict, List, Tuple, Union
from geoalchemy2.elements import WKBElement
from geoalchemy2.shape import from_shape, to_shape
import shapely.geometry
from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.geometry.base import BaseGeometry

EARTH_RADIUS_METERS = 6_371_008.8  # Authalic Earth radius for WGS84 geodesic calculation


class InvalidGeometryError(ValueError):
    """Raised when a geometry fails topological validity or coordinate range checks."""
    pass


def _validate_coordinate_bounds(coords: Any) -> None:
    """Recursively validate that coordinates are within WGS84 longitude [-180, 180] and latitude [-90, 90]."""
    if isinstance(coords, (list, tuple)):
        if len(coords) >= 2 and isinstance(coords[0], (int, float)) and isinstance(coords[1], (int, float)):
            lon, lat = coords[0], coords[1]
            if not (-180.0 <= lon <= 180.0):
                raise InvalidGeometryError(
                    f"Longitude {lon} out of valid WGS84 range [-180, 180]. Longitude must be in [-180, 180]."
                )
            if not (-90.0 <= lat <= 90.0):
                raise InvalidGeometryError(
                    f"Latitude {lat} out of valid WGS84 range [-90, 90]. Latitude must be in [-90, 90]."
                )
        else:
            for item in coords:
                _validate_coordinate_bounds(item)


def _validate_linear_rings_closed(coords: Any) -> None:
    """Recursively validate that polygon linear rings have >= 4 coordinates and first == last."""
    if isinstance(coords, (list, tuple)) and coords:
        if (
            isinstance(coords[0], (list, tuple))
            and len(coords[0]) >= 2
            and isinstance(coords[0][0], (int, float))
        ):
            if len(coords) < 4:
                raise InvalidGeometryError("Linear ring must contain at least 4 coordinate positions.")
            first = coords[0]
            last = coords[-1]
            if first[0] != last[0] or first[1] != last[1]:
                raise InvalidGeometryError(
                    "First and last coordinate must be identical (unclosed linear ring)."
                )
        else:
            for sub in coords:
                _validate_linear_rings_closed(sub)



def parse_geojson_to_shapely(geojson_data: Union[Dict[str, Any], str]) -> BaseGeometry:
    """Parse a GeoJSON dictionary or JSON string into a Shapely geometry with strict validation.

    Args:
        geojson_data: GeoJSON geometry dictionary or JSON string.

    Returns:
        BaseGeometry: Validated Shapely geometry.
    """
    if isinstance(geojson_data, str):
        try:
            geojson_data = json.loads(geojson_data)
        except Exception as exc:
            raise InvalidGeometryError(f"Invalid GeoJSON string: {exc}")

    if not isinstance(geojson_data, dict):
        raise InvalidGeometryError("GeoJSON geometry must be a dictionary.")

    geom_type = geojson_data.get("type")
    coords = geojson_data.get("coordinates")

    if not geom_type or coords is None:
        raise InvalidGeometryError("GeoJSON must contain 'type' and 'coordinates' fields.")

    _validate_coordinate_bounds(coords)
    if geom_type in ("Polygon", "MultiPolygon"):
        _validate_linear_rings_closed(coords)

    try:
        geom = shape(geojson_data)
    except Exception as exc:
        raise InvalidGeometryError(f"Failed to parse geometry: {exc}")

    if geom.is_empty:
        raise InvalidGeometryError("Geometry cannot be empty.")

    if not geom.is_valid:
        # Attempt minimal repair if invalid
        repaired = geom.buffer(0)
        if not repaired.is_valid or repaired.is_empty:
            raise InvalidGeometryError(
                f"Invalid geometry: {shapely.validation.explain_validity(geom)}"
            )
        geom = repaired

    return geom


def validate_geojson_polygon(geojson_data: Union[Dict[str, Any], str]) -> Polygon:
    """Validate and return a Shapely Polygon (used for Farm Zones)."""
    geom = parse_geojson_to_shapely(geojson_data)
    if isinstance(geom, Polygon):
        return geom
    elif isinstance(geom, MultiPolygon) and len(geom.geoms) == 1:
        return geom.geoms[0]
    else:
        raise InvalidGeometryError(
            f"Expected Polygon geometry for zone, but received {geom.geom_type}."
        )


def validate_geojson_multipolygon(
    geojson_data: Union[Dict[str, Any], str]
) -> MultiPolygon:
    """Validate and return a Shapely MultiPolygon (used for Farm Boundaries).

    If a single Polygon is provided, it is automatically converted into a MultiPolygon.
    """
    geom = parse_geojson_to_shapely(geojson_data)
    if isinstance(geom, MultiPolygon):
        return geom
    elif isinstance(geom, Polygon):
        return MultiPolygon([geom])
    else:
        raise InvalidGeometryError(
            f"Expected MultiPolygon or Polygon for farm boundary, but received {geom.geom_type}."
        )


def _ring_spherical_area(coords: List[Tuple[float, float]]) -> float:
    """Calculate geodesic surface area of a closed coordinate ring on the WGS84 sphere in square meters."""
    if len(coords) < 3:
        return 0.0

    rad_coords = [(math.radians(lon), math.radians(lat)) for lon, lat in coords]
    total = 0.0
    n = len(rad_coords)
    for i in range(n):
        p1 = rad_coords[i - 1]
        p2 = rad_coords[(i + 1) % n]
        total += (p2[0] - p1[0]) * math.sin(rad_coords[i][1])

    area_sq_m = abs(total * (EARTH_RADIUS_METERS**2) / 2.0)
    return area_sq_m


def calculate_geodesic_area_hectares(geom: BaseGeometry) -> float:
    """Calculate the geodesic area of a Polygon or MultiPolygon in hectares.

    Never calculates area directly from square degrees!
    1 hectare = 10,000 square meters.

    Returns:
        float: Calculated area in hectares, rounded to 4 decimal places.
    """
    if geom.is_empty:
        return 0.0

    total_sq_meters = 0.0

    def polygon_area(poly: Polygon) -> float:
        exterior_area = _ring_spherical_area(list(poly.exterior.coords))
        interiors_area = sum(
            _ring_spherical_area(list(interior.coords)) for interior in poly.interiors
        )
        return max(0.0, exterior_area - interiors_area)

    if isinstance(geom, Polygon):
        total_sq_meters = polygon_area(geom)
    elif isinstance(geom, MultiPolygon):
        total_sq_meters = sum(polygon_area(poly) for poly in geom.geoms)
    else:
        return 0.0

    hectares = total_sq_meters / 10_000.0
    return round(hectares, 4)


def check_zone_contained_in_farm(
    zone_geom: Polygon, farm_geom: Union[Polygon, MultiPolygon]
) -> bool:
    """Verify that a farm zone is strictly or almost completely contained within the farm boundary.

    Allows a tiny floating-point tolerance (e.g. 99.9% intersection) for minor edge alignment.
    """
    if farm_geom.is_empty or zone_geom.is_empty:
        return False

    if farm_geom.contains(zone_geom) or farm_geom.covers(zone_geom):
        return True

    # Check intersection overlap ratio to tolerate micro precision rounding at borders
    intersection = farm_geom.intersection(zone_geom)
    if not intersection.is_empty and intersection.area / zone_geom.area >= 0.999:
        return True

    return False


def geometry_to_geojson_dict(
    geom_source: Union[WKBElement, BaseGeometry, str, dict]
) -> Dict[str, Any]:
    """Convert a GeoAlchemy2 WKBElement or Shapely geometry to standard GeoJSON dictionary."""
    if isinstance(geom_source, dict):
        return geom_source

    if isinstance(geom_source, str):
        try:
            return json.loads(geom_source)
        except Exception:
            shapely_geom = shapely.wkt.loads(geom_source)
            return mapping(shapely_geom)

    if isinstance(geom_source, WKBElement):
        shapely_geom = to_shape(geom_source)
        return mapping(shapely_geom)

    if isinstance(geom_source, BaseGeometry):
        return mapping(geom_source)

    raise ValueError(f"Cannot serialize geometry of type {type(geom_source)}")
