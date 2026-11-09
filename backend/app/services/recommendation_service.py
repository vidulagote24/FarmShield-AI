"""Business service layer for Agronomic Recommendations."""

import uuid
from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.core.exceptions import AppException
from app.models.farm import FarmZone
from app.models.recommendation import Recommendation
from app.schemas.recommendation import RecommendationCreate, RecommendationUpdate
from app.services.observation_service import ZoneMismatchError


def create_recommendation(
    db: Session, farm_id: uuid.UUID, rec_in: RecommendationCreate
) -> Recommendation:
    """Create a new recommendation for a farm or zone."""
    if rec_in.zone_id:
        zone = db.query(FarmZone).filter(FarmZone.id == rec_in.zone_id).first()
        if not zone or zone.farm_id != farm_id:
            raise ZoneMismatchError(rec_in.zone_id, farm_id)

    recommendation = Recommendation(
        farm_id=farm_id,
        zone_id=rec_in.zone_id,
        recommendation_type=rec_in.recommendation_type,
        title=rec_in.title,
        description=rec_in.description,
        priority=rec_in.priority,
        status=rec_in.status,
        reasoning=rec_in.reasoning or {},
        recommended_action=rec_in.recommended_action or {},
        generated_at=rec_in.generated_at,
        valid_until=rec_in.valid_until,
    )
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)
    return recommendation


def get_recommendation_by_id(
    db: Session, recommendation_id: uuid.UUID
) -> Optional[Recommendation]:
    """Retrieve recommendation by UUID."""
    return db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()


def list_recommendations(
    db: Session,
    farm_id: Optional[uuid.UUID] = None,
    zone_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    active_only: bool = False,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Recommendation], int]:
    """List recommendations for a farm with filtering and pagination."""
    query = db.query(Recommendation)

    if farm_id:
        query = query.filter(Recommendation.farm_id == farm_id)
    if zone_id:
        query = query.filter(Recommendation.zone_id == zone_id)
    if status:
        query = query.filter(Recommendation.status == status.strip().lower())
    if priority:
        query = query.filter(Recommendation.priority == priority.strip().lower())
    if active_only:
        now = datetime.now(timezone.utc)
        query = query.filter((Recommendation.valid_until.is_(None)) | (Recommendation.valid_until >= now))
    if start_date:
        query = query.filter(Recommendation.generated_at >= start_date)
    if end_date:
        query = query.filter(Recommendation.generated_at <= end_date)

    total = query.count()
    offset = max(0, (page - 1) * page_size)
    items = (
        query.order_by(Recommendation.generated_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return items, total


def update_recommendation_status(
    db: Session, recommendation: Recommendation, new_status: str
) -> Recommendation:
    """Update status of a recommendation (accepted, rejected, completed)."""
    recommendation.status = new_status.strip().lower()
    db.commit()
    db.refresh(recommendation)
    return recommendation
