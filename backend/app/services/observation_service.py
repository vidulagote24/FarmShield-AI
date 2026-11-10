"""Business service layer for Farm and Zone Observations."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from app.core.exceptions import AppException
from app.core.logging import logger
from app.models.farm import Farm, FarmZone
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


def bulk_create_observations(
    db: Session,
    farm_id: uuid.UUID,
    observations_in: List[ObservationCreate],
    *,
    commit: bool = True,
    return_all: bool = False,
) -> List[Observation]:
    """Atomically ingest and deduplicate a batch of observations for a farm.

    Requirements enforced:
    1. Farm existence and zone boundary/foreign-key integrity verified prior to write.
    2. Atomic transaction boundary: the entire batch commits together; any error rolls back
       the entire transaction leaving 0 partial writes.
    3. Idempotent conflict-safe insertion: duplicates matching (farm_id, zone_id,
       observation_type, source, observed_at) via PostgreSQL's UNIQUE NULLS NOT DISTINCT
       constraint are safely ignored without raising duplicate key errors.
    4. Returns newly inserted Observation entities by default, or all matching
       persisted records if return_all=True.

    Args:
        db: SQLAlchemy session.
        farm_id: UUID of the farm receiving the observations.
        observations_in: List of ObservationCreate schema instances.
        commit: If True, commits the transaction upon batch success. If False,
            flushes so the caller can commit as part of an outer transaction.
        return_all: If True, returns all matching persisted observations (new + existing).
            If False (default), returns only the newly persisted observations.

    Returns:
        List[Observation]: Persisted Observation entities.
    """
    if not observations_in:
        return []

    # 1. Verify target farm exists
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise AppException(
            message=f"Farm '{farm_id}' was not found.",
            status_code=404,
            details={"farm_id": str(farm_id)},
        )

    # 2. Validate all specified zones belong to the target farm
    referenced_zone_ids = {
        obs.zone_id for obs in observations_in if obs.zone_id is not None
    }
    if referenced_zone_ids:
        existing_zones = (
            db.query(FarmZone.id)
            .filter(
                FarmZone.farm_id == farm_id,
                FarmZone.id.in_(referenced_zone_ids),
            )
            .all()
        )
        valid_zone_ids = {z[0] for z in existing_zones}
        for z_id in referenced_zone_ids:
            if z_id not in valid_zone_ids:
                raise ZoneMismatchError(z_id, farm_id)

    # 3. Normalize records and deduplicate within the input batch itself
    # Canonical identity tuple: (farm_id, zone_id, observation_type, source, observed_at_utc)
    records_dict: Dict[Tuple[uuid.UUID, Optional[uuid.UUID], str, str, datetime], Dict[str, Any]] = {}
    now_utc = datetime.now(timezone.utc)

    for obs in observations_in:
        ts = obs.observed_at
        ts_utc = ts.astimezone(timezone.utc) if ts.tzinfo is not None else ts.replace(tzinfo=timezone.utc)

        obs_type = obs.observation_type.strip().lower()
        source = obs.source.strip()
        key = (farm_id, obs.zone_id, obs_type, source, ts_utc)

        if key not in records_dict:
            records_dict[key] = {
                "id": uuid.uuid4(),
                "farm_id": farm_id,
                "zone_id": obs.zone_id,
                "observation_type": obs_type,
                "source": source,
                "observed_at": ts_utc,
                "value": obs.value,
                "unit": obs.unit.strip() if obs.unit else None,
                "metadata_json": obs.metadata_json or {},
                "created_at": now_utc,
            }

    records_to_insert = list(records_dict.values())
    if not records_to_insert:
        return []

    # 4. Atomic insertion using PostgreSQL ON CONFLICT DO NOTHING
    stmt = (
        pg_insert(Observation)
        .values(records_to_insert)
        .on_conflict_do_nothing(
            index_elements=["farm_id", "zone_id", "observation_type", "source", "observed_at"]
        )
        .returning(Observation)
    )

    try:
        with db.begin_nested():
            result = db.scalars(stmt).all()
            newly_inserted = list(result)

        if commit:
            db.commit()

        if return_all and len(newly_inserted) < len(records_to_insert):
            # Query all matching records for the batch
            timestamps = [r["observed_at"] for r in records_to_insert]
            all_records = (
                db.query(Observation)
                .filter(
                    Observation.farm_id == farm_id,
                    Observation.observed_at.in_(timestamps),
                )
                .all()
            )
            return all_records

        return newly_inserted
    except Exception as exc:
        db.rollback()
        logger.error(f"Bulk observation persistence failed for farm '{farm_id}': {exc}")
        raise


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
