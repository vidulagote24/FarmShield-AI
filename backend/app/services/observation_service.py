"""Business service layer for Farm and Zone Observations."""

import uuid
from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.core.exceptions import AppException
from app.models.farm import FarmZone
from app.models.observation import Observation
from app.schemas.observation import ObservationCreate


class ZoneMismatchError(AppException):
    """Raised when the specified zone does not belong to the target farm."""

    def __init__(self, zone_id: uuid.UUID, farm_id: uuid.UUID) -> None:
        super().__init__(
            message=f"Zone '{zone_id}' does not belong to farm '{farm_id}'.",
            status_code=400,
            details={"zone_id": str(zone_id), "farm_id": str(farm_id)},
        )


def create_observation(
    db: Session, farm_id: uuid.UUID, obs_in: ObservationCreate
) -> Observation:
    """Create an observation record, verifying zone integrity."""
    if obs_in.zone_id:
        zone = db.query(FarmZone).filter(FarmZone.id == obs_in.zone_id).first()
        if not zone or zone.farm_id != farm_id:
            raise ZoneMismatchError(obs_in.zone_id, farm_id)

    observation = Observation(
        farm_id=farm_id,
        zone_id=obs_in.zone_id,
        observation_type=obs_in.observation_type,
        source=obs_in.source,
        observed_at=obs_in.observed_at,
        value=obs_in.value,
        unit=obs_in.unit,
        metadata_json=obs_in.metadata_json or {},
    )
    db.add(observation)
    db.commit()
    db.refresh(observation)
    return observation


def get_observation_by_id(
    db: Session, observation_id: uuid.UUID
) -> Optional[Observation]:
    """Retrieve observation by UUID."""
    return db.query(Observation).filter(Observation.id == observation_id).first()


def list_observations(
    db: Session,
    farm_id: uuid.UUID,
    zone_id: Optional[uuid.UUID] = None,
    observation_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Observation], int]:
    """List observations for a farm with optional filters and pagination."""
    query = db.query(Observation).filter(Observation.farm_id == farm_id)

    if zone_id:
        query = query.filter(Observation.zone_id == zone_id)
    if observation_type:
        query = query.filter(Observation.observation_type == observation_type.strip().lower())
    if start_date:
        query = query.filter(Observation.observed_at >= start_date)
    if end_date:
        query = query.filter(Observation.observed_at <= end_date)

    total = query.count()
    offset = max(0, (page - 1) * page_size)
    items = (
        query.order_by(Observation.observed_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return items, total
