"""Tests for geometry validation, geodesic area calculations, and CRS operations.

Follows strict test integrity:
- Uses independent mathematical and geodesic calculations.
- Tests invalid, empty, out-of-bounds, and boundary cases.
"""

import pytest
from shapely.geometry import Polygon, MultiPolygon, box

from backend.app.intelligence.geospatial.geometry import (
    calculate_geodesic_area_m2,
    calculate_geodesic_area_ha,
    validate_polygon_geometry,
    check_zone_contained_in_farm,
    transform_geometry_crs,
)


def test_valid_polygon_geodesic_area_near_pune():
    """Verify that geodesic area matches expected physical dimensions on WGS84.

    A 0.001 deg x 0.001 deg bounding box at ~18.5 N, 73.8 E (near Pune, Maharashtra):
    - 0.001 deg lat ~= 110.7 meters
    - 0.001 deg lon at 18.5 deg N ~= 105.6 meters
    - Expected area ~= 110.7 * 105.6 ~= 11,690 m² (~1.17 ha).
    """
    pune_poly = box(73.800, 18.500, 73.801, 18.501)
    result = validate_polygon_geometry(pune_poly)

    assert result.is_valid is True
    assert result.error_message is None
    assert result.is_empty is False
    assert result.geometry_type == "Polygon"

    # Geodesic area must be physically realistic (~11,600 to 11,800 m²)
    assert result.area_m2 is not None
    assert 11600.0 < result.area_m2 < 11800.0

    # In hectares: 1 ha = 10,000 m²
    assert result.area_ha is not None
    assert 1.16 < result.area_ha < 1.18

    # Ensure area is not computed directly as naive degrees (0.001 * 0.001 = 1e-6)
    assert result.area_m2 > 1000.0


def test_invalid_self_intersecting_bowtie_polygon():
    """Verify that a self-intersecting 'bowtie' polygon is detected as invalid."""
    # Bowtie polygon crossing itself between vertices
    bowtie_coords = [
        (73.80, 18.50),
        (73.81, 18.51),
        (73.80, 18.51),
        (73.81, 18.50),
        (73.80, 18.50),
    ]
    invalid_poly = Polygon(bowtie_coords)
    result = validate_polygon_geometry(invalid_poly)

    assert result.is_valid is False
    assert result.error_message is not None
    assert "Invalid geometry topology" in result.error_message or "Self-intersection" in result.error_message
    assert result.area_m2 is None


def test_empty_polygon():
    """Verify that an empty polygon is correctly flagged as empty and invalid."""
    empty_poly = Polygon()
    result = validate_polygon_geometry(empty_poly)

    assert result.is_valid is False
    assert result.is_empty is True
    assert "empty" in result.error_message.lower()


def test_geojson_dict_input():
    """Verify that standard GeoJSON geometry dicts are accepted and validated."""
    geojson_polygon = {
        "type": "Polygon",
        "coordinates": [
            [
                [73.800, 18.500],
                [73.802, 18.500],
                [73.802, 18.502],
                [73.800, 18.502],
                [73.800, 18.500],
            ]
        ],
    }
    result = validate_polygon_geometry(geojson_polygon)
    assert result.is_valid is True
    assert result.geometry_type == "Polygon"
    assert result.area_ha > 0.0


def test_out_of_bounds_wgs84_coordinates():
    """Verify that coordinates outside [-180, 180] or [-90, 90] are rejected."""
    bad_poly = box(200.0, 10.0, 201.0, 11.0)
    result = validate_polygon_geometry(bad_poly, crs_str="EPSG:4326")

    assert result.is_valid is False
    assert "out of WGS84 bounds" in result.error_message


def test_zone_contained_in_farm():
    """Verify zone containment checks within a farm boundary."""
    farm_poly = box(73.80, 18.50, 73.85, 18.55)
    inside_zone = box(73.81, 18.51, 73.82, 18.52)
    outside_zone = box(73.84, 18.54, 73.86, 18.56)  # Protrudes beyond 73.85 / 18.55

    is_contained_in, outside_area_in = check_zone_contained_in_farm(farm_poly, inside_zone)
    assert is_contained_in is True
    assert outside_area_in == 0.0

    is_contained_out, outside_area_out = check_zone_contained_in_farm(farm_poly, outside_zone, tolerance_m2=1.0)
    assert is_contained_out is False
    assert outside_area_out > 100.0


def test_crs_transformation_to_utm():
    """Verify coordinate transformation from EPSG:4326 to UTM Zone 43N (Pune area)."""
    pune_poly = box(73.80, 18.50, 73.81, 18.51)
    utm_poly = transform_geometry_crs(pune_poly, src_crs="EPSG:4326", target_crs="EPSG:32643")

    # UTM coordinates for Pune (18.5 N, 73.8 E) are roughly:
    # Easting: ~373,000 m, Northing: ~2,046,000 m
    minx, miny, maxx, maxy = utm_poly.bounds
    assert 300000.0 < minx < 450000.0
    assert 2000000.0 < miny < 2100000.0


def test_polygon_with_hole_geodesic_area():
    """Verify that interior hole area is subtracted from geodesic area (donut polygon)."""
    # Outer box: 0.02 deg x 0.02 deg (~2.2 km x 2.1 km)
    outer = box(73.80, 18.50, 73.82, 18.52)
    # Inner hole: 0.01 deg x 0.01 deg in the center
    inner_coords = [
        (73.805, 18.505),
        (73.815, 18.505),
        (73.815, 18.515),
        (73.805, 18.515),
        (73.805, 18.505),
    ]
    donut_poly = Polygon(outer.exterior.coords, [inner_coords])
    solid_poly = Polygon(outer.exterior.coords)
    hole_poly = Polygon(inner_coords)

    area_donut = calculate_geodesic_area_m2(donut_poly)
    area_solid = calculate_geodesic_area_m2(solid_poly)
    area_hole = calculate_geodesic_area_m2(hole_poly)

    # Net area must equal solid area minus hole area
    assert pytest.approx(area_donut, abs=1.0) == (area_solid - area_hole)
    assert area_donut < area_solid


def test_multipolygon_geodesic_area():
    """Verify that MultiPolygon area is the sum of disjoint polygon areas."""
    poly1 = box(73.80, 18.50, 73.81, 18.51)
    poly2 = box(73.83, 18.53, 73.84, 18.54)
    multi = MultiPolygon([poly1, poly2])

    area_multi = calculate_geodesic_area_m2(multi)
    area_p1 = calculate_geodesic_area_m2(poly1)
    area_p2 = calculate_geodesic_area_m2(poly2)

    assert pytest.approx(area_multi, abs=0.1) == (area_p1 + area_p2)


def test_boundary_touching_adjacent_zones():
    """Verify that adjacent zones sharing a common boundary edge pass containment."""
    farm_poly = box(73.80, 18.50, 73.82, 18.51)
    # Zone 1 and Zone 2 share the boundary at longitude 73.81
    zone1 = box(73.80, 18.50, 73.81, 18.51)
    zone2 = box(73.81, 18.50, 73.82, 18.51)

    contained1, _ = check_zone_contained_in_farm(farm_poly, zone1)
    contained2, _ = check_zone_contained_in_farm(farm_poly, zone2)

    assert contained1 is True
    assert contained2 is True


def test_degenerate_collinear_polygon():
    """Verify that degenerate collapsed polygons (zero area) are flagged as invalid."""
    collinear_coords = [
        (73.80, 18.50),
        (73.81, 18.50),
        (73.82, 18.50),
        (73.80, 18.50),
    ]
    degenerate_poly = Polygon(collinear_coords)
    result = validate_polygon_geometry(degenerate_poly)

    assert result.is_valid is False
    assert "Degenerate" in result.error_message or "Invalid" in result.error_message


def test_very_small_geometry_micro_parcel():
    """Verify handling of micro-parcel geometry (~1 meter width)."""
    # 0.00001 deg ~= 1.1 meters
    micro_poly = box(73.80000, 18.50000, 73.80001, 18.50001)
    result = validate_polygon_geometry(micro_poly)

    assert result.is_valid is True
    # Area of ~1.1 m x ~1.05 m ~= 1.15 m²
    assert 0.5 < result.area_m2 < 3.0
    assert result.area_ha < 0.001

