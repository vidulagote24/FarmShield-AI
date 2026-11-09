"""API v1 Endpoints for Recommendations with Farm Ownership Protection."""

import math
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api.deps import check_farm_ownership, get_current_active_user, get_db
from app.models.farm import Farm
from app.models.recommendation import Recommendation
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.recommendation import (
    RecommendationCreate,
    RecommendationResponse,
    RecommendationStatusUpdate,
)
from app.services import recommendation_service

router = APIRouter(tags=["Recommendations"])


def _get_recommendation_and_verify_ownership(
    db: Session, recommendation_id: uuid.UUID, current_user: User
) -> Recommendation:
    rec = recommendation_service.get_recommendation_by_id(db, recommendation_id)
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation '{recommendation_id}' was not found.",
        )
    farm = db.query(Farm).filter(Farm.id == rec.farm_id).first()
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parent farm for recommendation '{recommendation_id}' was not found.",
        )
    check_farm_ownership(farm, current_user)
    return rec


@router.post(
    "/recommendations",
    response_model=RecommendationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a recommendation",
)
def create_recommendation(
    rec_in: RecommendationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RecommendationResponse:
    """Create an agronomic recommendation record for an owned farm."""
    if not rec_in.farm_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="farm_id is required when creating a recommendation.",
        )
    farm = db.query(Farm).filter(Farm.id == rec_in.farm_id).first()
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farm '{rec_in.farm_id}' was not found.",
        )
    check_farm_ownership(farm, current_user)
    return recommendation_service.create_recommendation(db, rec_in.farm_id, rec_in)


@router.get(
    "/recommendations",
    response_model=PaginatedResponse[RecommendationResponse],
    summary="Query recommendations with filters",
)
def list_recommendations(
    farm_id: Optional[uuid.UUID] = Query(None, description="Filter by farm UUID"),
    zone_id: Optional[uuid.UUID] = Query(None, description="Filter by zone UUID"),
    status: Optional[str] = Query(None, description="Filter by workflow status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    active_only: bool = Query(False, description="Filter only non-expired recommendations"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedResponse[RecommendationResponse]:
    """Query recommendations with farm ownership check."""
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
            detail="farm_id parameter is required to query recommendations.",
        )

    items, total = recommendation_service.list_recommendations(
        db,
        farm_id=farm_id,
        zone_id=zone_id,
        status=status,
        priority=priority,
        active_only=active_only,
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


@router.get(
    "/recommendations/{recommendation_id}",
    response_model=RecommendationResponse,
    summary="Get recommendation by UUID",
)
def get_recommendation(
    recommendation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RecommendationResponse:
    """Retrieve details for a specific recommendation with ownership check."""
    return _get_recommendation_and_verify_ownership(db, recommendation_id, current_user)


@router.patch(
    "/recommendations/{recommendation_id}/status",
    response_model=RecommendationResponse,
    summary="Update recommendation status",
)
def update_recommendation_status(
    recommendation_id: uuid.UUID,
    status_in: RecommendationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RecommendationResponse:
    """Update recommendation workflow status with ownership check."""
    rec = _get_recommendation_and_verify_ownership(db, recommendation_id, current_user)
    return recommendation_service.update_recommendation_status(
        db, rec, status_in.status
    )
