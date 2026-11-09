"""SQLAlchemy 2.x declarative model for Irrigation Events."""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class IrrigationEvent(Base):
    """Historical record of irrigation applied to a farm or specific zone."""

    __tablename__ = "irrigation_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("farms.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("farm_zones.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    irrigation_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    water_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    water_unit: Mapped[str] = mapped_column(
        String(50), default="liters", nullable=False
    )
    irrigation_method: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    farm: Mapped["Farm"] = relationship("Farm", back_populates="irrigation_events")
    zone: Mapped[Optional["FarmZone"]] = relationship(
        "FarmZone", back_populates="irrigation_events"
    )

    __table_args__ = (
        Index("ix_irrig_farm_date", "farm_id", "irrigation_date"),
        Index("ix_irrig_zone_date", "zone_id", "irrigation_date"),
    )

    def __repr__(self) -> str:
        return f"<IrrigationEvent id={self.id} farm_id={self.farm_id} quantity={self.water_quantity} {self.water_unit}>"
