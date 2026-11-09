"""Tests for Farm spatial validation, geodesic area calculation, and CRUD APIs."""

import pytest
from fastapi.testclient import TestClient


def test_create_farm_with_valid_multipolygon(
    auth_client: TestClient, test_farmer, sample_farm_multipolygon
):
    """Test creating a farm with valid MultiPolygon GeoJSON and verify calculated geodesic area."""
    payload = {
        "name": "Baramati Green Farm",
        "description": "High yield sugarcane and wheat farm",
        "location_name": "Baramati, Pune",
        "crop_type": "sugarcane",
        "crop_variety": "Co 86032",
        "boundary": sample_farm_multipolygon,
    }
    response = auth_client.post("/api/v1/farms", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["crop_type"] == payload["crop_type"]
    assert data["owner_id"] == str(test_farmer.id)
    # Area must be calculated automatically, positive and realistic (~116 hectares)
    assert data["area_hectares"] > 100
    assert data["area_hectares"] < 130
    assert data["boundary"]["type"] == "MultiPolygon"
    assert len(data["boundary"]["coordinates"]) == 1


def test_create_farm_polygon_converted_to_multipolygon(
    auth_client: TestClient, test_farmer, sample_inside_polygon
):
    """Test that a Polygon boundary payload is automatically promoted to MultiPolygon."""
    payload = {
        "name": "Plot A",
        "crop_type": "cotton",
        "boundary": sample_inside_polygon,
    }
    response = auth_client.post("/api/v1/farms", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["boundary"]["type"] == "MultiPolygon"
    assert data["area_hectares"] > 0


def test_create_farm_invalid_geometry_unclosed_ring(
    auth_client: TestClient, test_farmer
):
    """Verify that an unclosed polygon ring is rejected with 422 Unprocessable Entity."""
    unclosed_polygon = {
        "type": "Polygon",
        "coordinates": [
            [
                [73.8500, 18.5200],
                [73.8600, 18.5200],
                [73.8600, 18.5300],
                [73.8500, 18.5300],
                # Missing closing coordinate [73.8500, 18.5200]
            ]
        ],
    }
    payload = {
        "name": "Invalid Boundary Farm",
        "crop_type": "wheat",
        "boundary": unclosed_polygon,
    }
    response = auth_client.post("/api/v1/farms", json=payload)
    assert response.status_code == 422
    assert "First and last coordinate must be identical" in str(response.json())


def test_create_farm_invalid_coordinate_range(
    auth_client: TestClient, test_farmer
):
    """Verify that coordinates outside [-180, 180] or [-90, 90] are rejected with 422."""
    invalid_coords = {
        "type": "Polygon",
        "coordinates": [
            [
                [200.0000, 18.5200],  # Longitude > 180
                [200.0100, 18.5200],
                [200.0100, 18.5300],
                [200.0000, 18.5300],
                [200.0000, 18.5200],
            ]
        ],
    }
    payload = {
        "name": "Out of Range Farm",
        "crop_type": "rice",
        "boundary": invalid_coords,
    }
    response = auth_client.post("/api/v1/farms", json=payload)
    assert response.status_code == 422
    assert "Longitude must be in [-180, 180]" in str(response.json())


def test_get_and_update_farm(auth_client: TestClient, test_farmer, sample_farm_multipolygon):
    """Test retrieving and updating farm metadata."""
    create_res = auth_client.post("/api/v1/farms", json={
        "name": "Initial Farm",
        "crop_type": "maize",
        "boundary": sample_farm_multipolygon,
    })
    farm_id = create_res.json()["id"]

    # Get farm
    get_res = auth_client.get(f"/api/v1/farms/{farm_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Initial Farm"

    # Update metadata
    update_res = auth_client.put(f"/api/v1/farms/{farm_id}", json={
        "name": "Updated Farm Name",
        "crop_variety": "African Tall",
    })
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Updated Farm Name"
    assert update_res.json()["crop_variety"] == "African Tall"


def test_get_farm_boundary_geojson(auth_client: TestClient, test_farmer, sample_farm_multipolygon):
    """Test retrieving farm boundary specifically as GeoJSON geometry and calculated area."""
    create_res = auth_client.post("/api/v1/farms", json={
        "name": "GeoJSON Test Farm",
        "crop_type": "soybean",
        "boundary": sample_farm_multipolygon,
    })
    farm_id = create_res.json()["id"]

    res = auth_client.get(f"/api/v1/farms/{farm_id}/boundary")
    assert res.status_code == 200
    data = res.json()
    assert data["boundary"]["type"] == "MultiPolygon"
    assert data["name"] == "GeoJSON Test Farm"
    assert data["area_hectares"] > 0


def test_update_farm_boundary(
    auth_client: TestClient, test_farmer, sample_farm_multipolygon, sample_inside_polygon
):
    """Test updating farm boundary recalculates area_hectares."""
    create_res = auth_client.post("/api/v1/farms", json={
        "name": "Boundary Change Farm",
        "crop_type": "onion",
        "boundary": sample_farm_multipolygon,
    })
    farm_id = create_res.json()["id"]
    initial_area = create_res.json()["area_hectares"]

    # Update boundary to smaller polygon
    update_res = auth_client.put(f"/api/v1/farms/{farm_id}/boundary", json={
        "boundary": sample_inside_polygon,
    })
    assert update_res.status_code == 200
    new_area = update_res.json()["area_hectares"]
    assert new_area < initial_area
    assert new_area > 0
