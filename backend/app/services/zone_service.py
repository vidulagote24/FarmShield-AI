"""Business service layer for Farm Zones and spatial containment validation."""

import uuid
from typing import List, Optional, Tuple
from geoalchemy2.shape import from_shape, to_shape
from sqlalchemy.orm import Session
from app.core.exceptions import AppException
from app.core.spatial import (
    calculate_geodesic_area_hectares,
    check_zone_contained_in_farm,
    validate_geojson_polygon,
)
from app.models.farm import Farm, FarmZone
from app.schemas.farm import FarmZoneCreate, FarmZoneUpdate


class ZoneContainmentError(AppException):
    """Raised when a farm zone is not contained within its parent farm boundary."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, status_code=400)


class DuplicateZoneCodeError(AppException):
    """Raised when a zone code is already taken within the same farm."""

    def __init__(self, code: str) -> None:
        super().__init__(
            message=f"Zone code '{code}' already exists within this farm.",
            status_code=409,
            details={"zone_code": code},
        )


def create_zone(db: Session, farm: Farm, zone_in: FarmZoneCreate) -> FarmZone:
    """Create a new zone within a farm, validating spatial containment."""
    # Check zone code uniqueness within farm
    existing = (
        db.query(FarmZone)
        .filter(FarmZone.farm_id == farm.id, FarmZone.zone_code == zone_in.zone_code)
        .first()
    )
    if existing:
        raise DuplicateZoneCodeError(zone_in.zone_code)

    # Validate geometry
    zone_shapely = validate_geojson_polygon(zone_in.boundary)
    farm_shapely = to_shape(farm.boundary)

    # Verify spatial containment
    if not check_zone_contained_in_farm(zone_shapely, farm_shapely):
        raise ZoneContainmentError(
            f"Zone boundary must be completely contained within the farm boundary: zone '{zone_in.zone_name}' exceeds parent farm '{farm.name}'."
        )

    area_ha = calculate_geodesic_area_hectares(zone_shapely)
    if area_ha <= 0.0:
        raise ZoneContainmentError("Calculated zone area must be greater than zero hectares.")

    zone = FarmZone(
        farm_id=farm.id,
        zone_name=zone_in.zone_name,
        zone_code=zone_in.zone_code,
        boundary=from_shape(zone_shapely, srid=4326),
        area_hectares=area_ha,
        metadata_json=zone_in.metadata_json or {},
    )
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


def get_zone_by_id(db: Session, zone_id: uuid.UUID) -> Optional[FarmZone]:
    """Retrieve zone by UUID."""
    return db.query(FarmZone).filter(FarmZone.id == zone_id).first()


def list_zones_by_farm(
    db: Session,
    farm_id: uuid.UUID,
    page: int = 1,
    page_size: int = 50,
) -> Tuple[List[FarmZone], int]:
    """List all zones for a given farm with pagination."""
    query = db.query(FarmZone).filter(FarmZone.farm_id == farm_id)
    total = query.count()
    offset = max(0, (page - 1) * page_size)
    items = query.order_by(FarmZone.zone_code.asc()).offset(offset).limit(page_size).all()
    return items, total


def update_zone(db: Session, zone: FarmZone, zone_in: FarmZoneUpdate) -> FarmZone:
    """Update a zone, verifying spatial containment if boundary changes."""
    if zone_in.zone_code and zone_in.zone_code != zone.zone_code:
        existing = (
            db.query(FarmZone)
            .filter(
                FarmZone.farm_id == zone.farm_id,
                FarmZone.zone_code == zone_in.zone_code,
                FarmZone.id != zone.id,
            )
            .first()
        )
        if existing:
            raise DuplicateZoneCodeError(zone_in.zone_code)
        zone.zone_code = zone_in.zone_code

    if zone_in.zone_name is not None:
        zone.zone_name = zone_in.zone_name

    if zone_in.metadata_json is not None:
        zone.metadata_json = zone_in.metadata_json

    if zone_in.boundary is not None:
        new_zone_shapely = validate_geojson_polygon(zone_in.boundary)
        farm_shapely = to_shape(zone.farm.boundary)

        if not check_zone_contained_in_farm(new_zone_shapely, farm_shapely):
            raise ZoneContainmentError(
                f"Updated boundary for zone '{zone.zone_name}' exceeds parent farm boundary."
            )

        new_area_ha = calculate_geodesic_area_hectares(new_zone_shapely)
        zone.boundary = from_shape(new_zone_shapely, srid=4326)
        zone.area_hectares = new_area_ha

    db.commit()
    db.refresh(zone)
    return zone


def delete_zone(db: Session, zone: FarmZone) -> None:
    """Delete a zone."""
    db.delete(zone)
    db.commit()
