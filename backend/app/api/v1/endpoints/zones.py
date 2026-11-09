"""API v1 Endpoints for Farm Zones (Individual CRUD with Farm Ownership Protection)."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import check_farm_ownership, get_current_active_user, get_db
from app.models.farm import Farm, FarmZone
from app.models.user import User
from app.schemas.farm import FarmZoneResponse, FarmZoneUpdate
from app.services import zone_service

router = APIRouter(tags=["Farm Zones"])


def _get_zone_and_verify_ownership(
    db: Session, zone_id: uuid.UUID, farm_id: Optional[uuid.UUID], current_user: User
) -> FarmZone:
    zone = zone_service.get_zone_by_id(db, zone_id)
    if not zone or (farm_id and zone.farm_id != farm_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone '{zone_id}' was not found.",
        )
    farm = db.query(Farm).filter(Farm.id == zone.farm_id).first()
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parent farm for zone '{zone_id}' was not found.",
        )
    check_farm_ownership(farm, current_user)
    return zone


@router.get(
    "/zones/{zone_id}",
    response_model=FarmZoneResponse,
    summary="Get zone by UUID",
)
@router.get(
    "/farms/{farm_id}/zones/{zone_id}",
    response_model=FarmZoneResponse,
    include_in_schema=False,
)
def get_zone(
    zone_id: uuid.UUID,
    farm_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FarmZoneResponse:
    """Retrieve details of a specific farm zone with ownership check."""
    return _get_zone_and_verify_ownership(db, zone_id, farm_id, current_user)


@router.put(
    "/zones/{zone_id}",
    response_model=FarmZoneResponse,
    summary="Update zone details or boundary",
)
@router.put(
    "/farms/{farm_id}/zones/{zone_id}",
    response_model=FarmZoneResponse,
    include_in_schema=False,
)
def update_zone(
    zone_id: uuid.UUID,
    zone_in: FarmZoneUpdate,
    farm_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FarmZoneResponse:
    """Update zone metadata or boundary geometry with ownership check."""
    zone = _get_zone_and_verify_ownership(db, zone_id, farm_id, current_user)
    return zone_service.update_zone(db, zone, zone_in)


@router.delete(
    "/zones/{zone_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete zone",
)
@router.delete(
    "/farms/{farm_id}/zones/{zone_id}",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def delete_zone(
    zone_id: uuid.UUID,
    farm_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Remove a zone from a farm with ownership check."""
    zone = _get_zone_and_verify_ownership(db, zone_id, farm_id, current_user)
    zone_service.delete_zone(db, zone)
    return {"message": "Zone deleted successfully."}
