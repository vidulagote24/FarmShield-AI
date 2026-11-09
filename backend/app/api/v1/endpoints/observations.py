"""API v1 Endpoints for Observations with Farm Ownership Protection."""

import math
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api.deps import check_farm_ownership, get_current_active_user, get_db
from app.models.farm import Farm
from app.models.observation import Observation
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.observation import ObservationCreate, ObservationResponse
from app.services import observation_service

router = APIRouter(tags=["Observations"])


def _get_observation_and_verify_ownership(
    db: Session, observation_id: uuid.UUID, current_user: User
) -> Observation:
    obs = observation_service.get_observation_by_id(db, observation_id)
    if not obs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation '{observation_id}' was not found.",
        )
    farm = db.query(Farm).filter(Farm.id == obs.farm_id).first()
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parent farm for observation '{observation_id}' was not found.",
        )
    check_farm_ownership(farm, current_user)
    return obs


@router.post(
    "/observations",
    response_model=ObservationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record an observation",
)
def create_observation(
    obs_in: ObservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ObservationResponse:
    """Create an observation record for an owned farm."""
    if not obs_in.farm_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="farm_id is required when creating an observation.",
        )
    farm = db.query(Farm).filter(Farm.id == obs_in.farm_id).first()
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farm '{obs_in.farm_id}' was not found.",
        )
    check_farm_ownership(farm, current_user)
    return observation_service.create_observation(db, obs_in.farm_id, obs_in)


@router.get(
    "/observations",
    response_model=PaginatedResponse[ObservationResponse],
    summary="Query observations with filters",
)
def list_observations(
    farm_id: Optional[uuid.UUID] = Query(None, description="Filter by farm UUID"),
    zone_id: Optional[uuid.UUID] = Query(None, description="Filter by zone UUID"),
    observation_type: Optional[str] = Query(None, description="Filter by observation type"),
    start_date: Optional[datetime] = Query(None, description="Filter observed_at >= start_date"),
    end_date: Optional[datetime] = Query(None, description="Filter observed_at <= end_date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedResponse[ObservationResponse]:
    """Query observations with farm ownership verification."""
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
            detail="farm_id parameter is required to query observations.",
        )

    items, total = observation_service.list_observations(
        db,
        farm_id=farm_id,
        zone_id=zone_id,
        observation_type=observation_type,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse[ObservationResponse](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get(
    "/observations/{observation_id}",
    response_model=ObservationResponse,
    summary="Get observation by UUID",
)
def get_observation(
    observation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ObservationResponse:
    """Retrieve details of a single observation record with ownership check."""
    return _get_observation_and_verify_ownership(db, observation_id, current_user)


@router.delete(
    "/observations/{observation_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete observation",
)
def delete_observation(
    observation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Delete an observation record with ownership check."""
    obs = _get_observation_and_verify_ownership(db, observation_id, current_user)
    observation_service.delete_observation(db, obs)
    return {"message": "Observation deleted successfully."}
