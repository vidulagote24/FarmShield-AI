"""Business service layer for Irrigation Events."""

import uuid
from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.farm import FarmZone
from app.models.irrigation import IrrigationEvent
from app.schemas.irrigation import IrrigationEventCreate, IrrigationEventUpdate
from app.services.observation_service import ZoneMismatchError


def create_irrigation_event(
    db: Session, farm_id: uuid.UUID, event_in: IrrigationEventCreate
) -> IrrigationEvent:
    """Create an irrigation event record, checking zone integrity."""
    if event_in.zone_id:
        zone = db.query(FarmZone).filter(FarmZone.id == event_in.zone_id).first()
        if not zone or zone.farm_id != farm_id:
            raise ZoneMismatchError(event_in.zone_id, farm_id)

    event = IrrigationEvent(
        farm_id=farm_id,
        zone_id=event_in.zone_id,
        irrigation_date=event_in.irrigation_date,
        water_quantity=event_in.water_quantity,
        water_unit=event_in.water_unit,
        irrigation_method=event_in.irrigation_method,
        notes=event_in.notes,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_irrigation_event_by_id(
    db: Session, event_id: uuid.UUID
) -> Optional[IrrigationEvent]:
    """Retrieve irrigation event by UUID."""
    return db.query(IrrigationEvent).filter(IrrigationEvent.id == event_id).first()


def list_irrigation_events(
    db: Session,
    farm_id: uuid.UUID,
    zone_id: Optional[uuid.UUID] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[IrrigationEvent], int]:
    """List irrigation events for a farm with optional filters and pagination."""
    query = db.query(IrrigationEvent).filter(IrrigationEvent.farm_id == farm_id)

    if zone_id:
        query = query.filter(IrrigationEvent.zone_id == zone_id)
    if start_date:
        query = query.filter(IrrigationEvent.irrigation_date >= start_date)
    if end_date:
        query = query.filter(IrrigationEvent.irrigation_date <= end_date)

    total = query.count()
    offset = max(0, (page - 1) * page_size)
    items = (
        query.order_by(IrrigationEvent.irrigation_date.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return items, total


def update_irrigation_event(
    db: Session, event: IrrigationEvent, event_in: IrrigationEventUpdate
) -> IrrigationEvent:
    """Update irrigation event attributes."""
    if event_in.zone_id is not None:
        if event_in.zone_id:
            zone = db.query(FarmZone).filter(FarmZone.id == event_in.zone_id).first()
            if not zone or zone.farm_id != event.farm_id:
                raise ZoneMismatchError(event_in.zone_id, event.farm_id)
        event.zone_id = event_in.zone_id

    if event_in.irrigation_date is not None:
        event.irrigation_date = event_in.irrigation_date
    if event_in.water_quantity is not None:
        event.water_quantity = event_in.water_quantity
    if event_in.water_unit is not None:
        event.water_unit = event_in.water_unit
    if event_in.irrigation_method is not None:
        event.irrigation_method = event_in.irrigation_method
    if event_in.notes is not None:
        event.notes = event_in.notes

    db.commit()
    db.refresh(event)
    return event


def delete_irrigation_event(db: Session, event: IrrigationEvent) -> None:
    """Delete an irrigation event."""
    db.delete(event)
    db.commit()
