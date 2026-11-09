"""Business service layer for Farms and Geospatial Boundaries."""

import uuid
from typing import Any, Dict, List, Optional, Tuple
from geoalchemy2.shape import from_shape, to_shape
from sqlalchemy.orm import Session
from app.core.exceptions import AppException
from app.core.spatial import (
    calculate_geodesic_area_hectares,
    check_zone_contained_in_farm,
    validate_geojson_multipolygon,
)
from app.models.farm import Farm, FarmZone
from app.schemas.farm import FarmCreate, FarmUpdate


class BoundaryValidationError(AppException):
    """Raised when spatial boundary is invalid or causes containment violations."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, status_code=400)


def create_farm(db: Session, farm_in: FarmCreate, owner_id: uuid.UUID) -> Farm:
    """Create a new farm with validated PostGIS MultiPolygon geometry and calculated geodesic area."""
    shapely_geom = validate_geojson_multipolygon(farm_in.boundary)
    area_ha = calculate_geodesic_area_hectares(shapely_geom)

    if area_ha <= 0.0:
        raise BoundaryValidationError("Calculated farm area must be greater than zero hectares.")

    wkb_boundary = from_shape(shapely_geom, srid=4326)

    farm = Farm(
        owner_id=owner_id,
        name=farm_in.name,
        description=farm_in.description,
        location_name=farm_in.location_name,
        crop_type=farm_in.crop_type,
        crop_variety=farm_in.crop_variety,
        sowing_date=farm_in.sowing_date,
        boundary=wkb_boundary,
        area_hectares=area_ha,
    )
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm


def get_farm_by_id(db: Session, farm_id: uuid.UUID) -> Optional[Farm]:
    """Retrieve farm by UUID."""
    return db.query(Farm).filter(Farm.id == farm_id).first()


def list_farms(
    db: Session,
    owner_id: Optional[uuid.UUID] = None,
    crop_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Farm], int]:
    """List farms with optional filtering and pagination."""
    query = db.query(Farm)
    if owner_id:
        query = query.filter(Farm.owner_id == owner_id)
    if crop_type:
        query = query.filter(Farm.crop_type.ilike(f"%{crop_type}%"))

    total = query.count()
    offset = max(0, (page - 1) * page_size)
    items = query.order_by(Farm.created_at.desc()).offset(offset).limit(page_size).all()
    return items, total


def update_farm(db: Session, farm: Farm, farm_in: FarmUpdate) -> Farm:
    """Update descriptive attributes of a farm."""
    update_data = farm_in.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        if val is not None:
            setattr(farm, key, val)

    db.commit()
    db.refresh(farm)
    return farm


def update_farm_boundary(
    db: Session, farm: Farm, boundary_geojson: Dict[str, Any]
) -> Farm:
    """Update farm boundary geometry with containment verification of existing zones."""
    new_shapely_geom = validate_geojson_multipolygon(boundary_geojson)
    new_area_ha = calculate_geodesic_area_hectares(new_shapely_geom)

    if new_area_ha <= 0.0:
        raise BoundaryValidationError("Calculated farm area must be greater than zero hectares.")

    # Verify that all existing farm zones remain contained in the new farm boundary
    existing_zones = db.query(FarmZone).filter(FarmZone.farm_id == farm.id).all()
    for zone in existing_zones:
        zone_shapely = to_shape(zone.boundary)
        if not check_zone_contained_in_farm(zone_shapely, new_shapely_geom):
            raise BoundaryValidationError(
                f"Existing zone '{zone.zone_name}' (code: {zone.zone_code}) falls outside the new farm boundary."
            )

    farm.boundary = from_shape(new_shapely_geom, srid=4326)
    farm.area_hectares = new_area_ha

    db.commit()
    db.refresh(farm)
    return farm


def delete_farm(db: Session, farm: Farm) -> None:
    """Delete a farm and its associated zones."""
    db.delete(farm)
    db.commit()
