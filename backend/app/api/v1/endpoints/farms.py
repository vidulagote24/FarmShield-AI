"""API v1 Endpoints for Farms, Boundaries, Zones, Observations, Recommendations, and Irrigation."""

import math
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api.deps import check_farm_ownership, get_current_active_user, get_db
from app.models.farm import Farm
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.farm import (
    FarmBoundaryResponse,
    FarmBoundaryUpdate,
    FarmCreate,
    FarmResponse,
    FarmUpdate,
    FarmZoneCreate,
    FarmZoneResponse,
)
from app.schemas.irrigation import IrrigationEventCreate, IrrigationEventResponse
from app.schemas.observation import ObservationCreate, ObservationResponse
from app.schemas.recommendation import RecommendationCreate, RecommendationResponse
from app.services import (
    farm_service,
    irrigation_service,
    observation_service,
    recommendation_service,
    zone_service,
)

router = APIRouter(tags=["Farms & Geospatial Boundaries"])


def _get_farm_or_404(db: Session, farm_id: uuid.UUID) -> Farm:
    farm = farm_service.get_farm_by_id(db, farm_id)
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farm '{farm_id}' was not found.",
        )
    return farm


# --- Farm CRUD ---


@router.post(
    "/farms",
    response_model=FarmResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new farm",
)
def create_farm(
    farm_in: FarmCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Farm:
    """Create a new farm owned by the authenticated farmer user."""
    return farm_service.create_farm(db, farm_in, owner_id=current_user.id)


@router.get(
    "/farms",
    response_model=PaginatedResponse[FarmResponse],
    summary="List farms",
)
def list_farms(
    owner_id: Optional[uuid.UUID] = Query(None, description="Filter by owner UUID"),
    crop_type: Optional[str] = Query(None, description="Filter by crop type name"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedResponse[FarmResponse]:
    """List farms with ownership isolation.

    Farmers can only view farms that they own. Administrators may view all
    farms or filter by any owner.
    """
    if current_user.role != "admin":
        if owner_id and owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to query other farmers' farms.",
            )
        effective_owner_id = current_user.id
    else:
        effective_owner_id = owner_id

    items, total = farm_service.list_farms(
        db, owner_id=effective_owner_id, crop_type=crop_type, page=page, page_size=page_size
    )
    return PaginatedResponse[FarmResponse](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get(
    "/farms/{farm_id}",
    response_model=FarmResponse,
    summary="Get farm details",
)
def get_farm(
    farm_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Farm:
    """Retrieve details for a specific farm by UUID with ownership verification."""
    farm = _get_farm_or_404(db, farm_id)
    check_farm_ownership(farm, current_user)
    return farm


@router.put(
    "/farms/{farm_id}",
    response_model=FarmResponse,
    summary="Update farm descriptive details",
)
def update_farm(
    farm_id: uuid.UUID,
    farm_in: FarmUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Farm:
    """Update metadata for an existing farm owned by authenticated user."""
    farm = _get_farm_or_404(db, farm_id)
    check_farm_ownership(farm, current_user)
    return farm_service.update_farm(db, farm, farm_in)


@router.delete(
    "/farms/{farm_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete farm",
)
def delete_farm(
    farm_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Delete a farm and its dependent zones, verifying ownership."""
    farm = _get_farm_or_404(db, farm_id)
    check_farm_ownership(farm, current_user)
    farm_service.delete_farm(db, farm)


# --- Farm Boundary ---


@router.put(
    "/farms/{farm_id}/boundary",
    response_model=FarmResponse,
    summary="Update farm spatial boundary",
)
def update_farm_boundary(
    farm_id: uuid.UUID,
    boundary_in: FarmBoundaryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Farm:
    """Update the PostGIS boundary of a farm, verifying ownership and spatial containment."""
    farm = _get_farm_or_404(db, farm_id)
    check_farm_ownership(farm, current_user)
    return farm_service.update_farm_boundary(db, farm, boundary_in.boundary)


@router.get(
    "/farms/{farm_id}/boundary",
    response_model=FarmBoundaryResponse,
    summary="Get farm boundary GeoJSON",
)
def get_farm_boundary(
    farm_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FarmBoundaryResponse:
    """Retrieve GeoJSON boundary and calculated geodesic area in hectares for a farm."""
    farm = _get_farm_or_404(db, farm_id)
    check_farm_ownership(farm, current_user)
    return FarmBoundaryResponse(
        id=farm.id,
        name=farm.name,
        boundary=farm.boundary,
        area_hectares=farm.area_hectares,
    )


# --- Farm Zones Sub-resource ---


@router.post(
    "/farms/{farm_id}/zones",
    response_model=FarmZoneResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a zone within a farm",
)
def create_farm_zone(
    farm_id: uuid.UUID,
    zone_in: FarmZoneCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FarmZoneResponse:
    """Create a new zone within a farm, validating ownership and spatial containment."""
    farm = _get_farm_or_404(db, farm_id)
    check_farm_ownership(farm, current_user)
    return zone_service.create_zone(db, farm, zone_in)


@router.get(
    "/farms/{farm_id}/zones",
    response_model=PaginatedResponse[FarmZoneResponse],
    summary="List zones within a farm",
)
def list_farm_zones(
    farm_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedResponse[FarmZoneResponse]:
    """List all zones established within the specified farm."""
    farm = _get_farm_or_404(db, farm_id)
    check_farm_ownership(farm, current_user)
    items, total = zone_service.list_zones_by_farm(
        db, farm_id, page=page, page_size=page_size
    )
    return PaginatedResponse[FarmZoneResponse](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


# --- Farm Observations Sub-resource ---


@router.post(
    "/farms/{farm_id}/observations",
    response_model=ObservationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record an observation for a farm",
)
def create_farm_observation(
    farm_id: uuid.UUID,
    obs_in: ObservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ObservationResponse:
    """Record a sensor, weather, or manual observation for an owned farm."""
    farm = _get_farm_or_404(db, farm_id)
    check_farm_ownership(farm, current_user)
    return observation_service.create_observation(db, farm_id, obs_in)


@router.get(
    "/farms/{farm_id}/observations",
    response_model=PaginatedResponse[ObservationResponse],
    summary="List observations for a farm",
)
def list_farm_observations(
    farm_id: uuid.UUID,
    zone_id: Optional[uuid.UUID] = Query(None, description="Filter by zone UUID"),
    observation_type: Optional[str] = Query(None, description="Filter by observation type"),
    start_date: Optional[datetime] = Query(None, description="Filter observed_at >= start_date"),
    end_date: Optional[datetime] = Query(None, description="Filter observed_at <= end_date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedResponse[ObservationResponse]:
    """Retrieve observations for an owned farm with optional filters."""
    farm = _get_farm_or_404(db, farm_id)
    check_farm_ownership(farm, current_user)
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


# --- Farm Recommendations Sub-resource ---


@router.post(
    "/farms/{farm_id}/recommendations",
    response_model=RecommendationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an agronomic recommendation",
)
def create_farm_recommendation(
    farm_id: uuid.UUID,
    rec_in: RecommendationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RecommendationResponse:
    """Register an advisory recommendation for an owned farm or zone."""
    farm = _get_farm_or_404(db, farm_id)
    check_farm_ownership(farm, current_user)
    return recommendation_service.create_recommendation(db, farm_id, rec_in)


@router.get(
    "/farms/{farm_id}/recommendations",
    response_model=PaginatedResponse[RecommendationResponse],
    summary="List recommendations for a farm",
)
def list_farm_recommendations(
    farm_id: uuid.UUID,
    zone_id: Optional[uuid.UUID] = Query(None, description="Filter by zone UUID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    start_date: Optional[datetime] = Query(None, description="Filter generated_at >= start_date"),
    end_date: Optional[datetime] = Query(None, description="Filter generated_at <= end_date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedResponse[RecommendationResponse]:
    """List recommendations for an owned farm with filtering and pagination."""
    farm = _get_farm_or_404(db, farm_id)
    check_farm_ownership(farm, current_user)
    items, total = recommendation_service.list_recommendations(
        db,
        farm_id=farm_id,
        zone_id=zone_id,
        status=status_filter,
        priority=priority,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse[RecommendationResponse](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


# --- Farm Irrigation Events Sub-resource ---


@router.post(
    "/farms/{farm_id}/irrigation-events",
    response_model=IrrigationEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record an irrigation event",
)
def create_farm_irrigation_event(
    farm_id: uuid.UUID,
    event_in: IrrigationEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> IrrigationEventResponse:
    """Log an irrigation activity for an owned farm or zone."""
    farm = _get_farm_or_404(db, farm_id)
    check_farm_ownership(farm, current_user)
    return irrigation_service.create_irrigation_event(db, farm_id, event_in)


@router.get(
    "/farms/{farm_id}/irrigation-events",
    response_model=PaginatedResponse[IrrigationEventResponse],
    summary="List irrigation events for a farm",
)
def list_farm_irrigation_events(
    farm_id: uuid.UUID,
    zone_id: Optional[uuid.UUID] = Query(None, description="Filter by zone UUID"),
    start_date: Optional[datetime] = Query(None, description="Filter irrigation_date >= start_date"),
    end_date: Optional[datetime] = Query(None, description="Filter irrigation_date <= end_date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedResponse[IrrigationEventResponse]:
    """Retrieve irrigation history for an owned farm with pagination."""
    farm = _get_farm_or_404(db, farm_id)
    check_farm_ownership(farm, current_user)
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
