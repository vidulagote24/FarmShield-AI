"""API v1 Endpoints for Irrigation Events with Farm Ownership Protection."""

import math
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api.deps import check_farm_ownership, get_current_active_user, get_db
from app.models.farm import Farm
from app.models.irrigation import IrrigationEvent
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.irrigation import (
    IrrigationEventCreate,
    IrrigationEventResponse,
    IrrigationEventUpdate,
)
from app.services import irrigation_service

router = APIRouter(tags=["Irrigation Events"])


def _get_irrigation_and_verify_ownership(
    db: Session, event_id: uuid.UUID, current_user: User
) -> IrrigationEvent:
    event = irrigation_service.get_irrigation_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Irrigation event '{event_id}' was not found.",
        )
    farm = db.query(Farm).filter(Farm.id == event.farm_id).first()
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parent farm for irrigation event '{event_id}' was not found.",
        )
    check_farm_ownership(farm, current_user)
    return event


@router.post(
    "/irrigation",
    response_model=IrrigationEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record an irrigation event",
)
def create_irrigation(
    event_in: IrrigationEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> IrrigationEventResponse:
    """Record an irrigation event for an owned farm."""
    if not event_in.farm_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="farm_id is required when creating an irrigation event.",
        )
    farm = db.query(Farm).filter(Farm.id == event_in.farm_id).first()
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farm '{event_in.farm_id}' was not found.",
        )
    check_farm_ownership(farm, current_user)
    return irrigation_service.create_irrigation_event(db, event_in.farm_id, event_in)


@router.get(
    "/irrigation",
    response_model=PaginatedResponse[IrrigationEventResponse],
    summary="Query irrigation history",
)
def list_irrigation(
    farm_id: Optional[uuid.UUID] = Query(None, description="Filter by farm UUID"),
    zone_id: Optional[uuid.UUID] = Query(None, description="Filter by zone UUID"),
    start_date: Optional[datetime] = Query(None, description="Filter irrigation_date >= start_date"),
    end_date: Optional[datetime] = Query(None, description="Filter irrigation_date <= end_date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedResponse[IrrigationEventResponse]:
    """Query irrigation events with farm ownership verification."""
    if farm_id:
        farm = db.query(Farm).filter(Farm.id == farm_id).first()
        if not farm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Farm '{farm_id}' was not found.",
            )
        check_farm_ownership(farm, current_user)
    elif current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="farm_id parameter is required to query irrigation events.",
        )

    items, total = irrigation_service.list_irrigation_events(
        db,
        farm_id=farm_id,
        zone_id=zone_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse[IrrigationEventResponse](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get(
    "/irrigation/{event_id}",
    response_model=IrrigationEventResponse,
    summary="Get irrigation event by UUID",
)
@router.get(
    "/irrigation-events/{event_id}",
    response_model=IrrigationEventResponse,
    include_in_schema=False,
)
def get_irrigation_event(
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> IrrigationEventResponse:
    """Retrieve details of an irrigation event record with ownership check."""
    return _get_irrigation_and_verify_ownership(db, event_id, current_user)


@router.put(
    "/irrigation/{event_id}",
    response_model=IrrigationEventResponse,
    summary="Update irrigation event",
)
@router.put(
    "/irrigation-events/{event_id}",
    response_model=IrrigationEventResponse,
    include_in_schema=False,
)
def update_irrigation_event(
    event_id: uuid.UUID,
    event_in: IrrigationEventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> IrrigationEventResponse:
    """Update details of an existing irrigation event record with ownership check."""
    event = _get_irrigation_and_verify_ownership(db, event_id, current_user)
    return irrigation_service.update_irrigation_event(db, event, event_in)


@router.delete(
    "/irrigation/{event_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete irrigation event",
)
@router.delete(
    "/irrigation-events/{event_id}",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def delete_irrigation_event(
    event_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Delete an irrigation event record with ownership check."""
    event = _get_irrigation_and_verify_ownership(db, event_id, current_user)
    irrigation_service.delete_irrigation_event(db, event)
    return {"message": "Irrigation event deleted successfully."}
