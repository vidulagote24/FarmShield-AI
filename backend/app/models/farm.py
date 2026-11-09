"""SQLAlchemy 2.x declarative models for Farms and Farm Zones with PostGIS spatial geometries."""

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from geoalchemy2 import Geometry
from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Farm(Base):
    """Agricultural Farm entity owned by a farmer with a PostGIS MultiPolygon boundary."""

    __tablename__ = "farms"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    crop_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    crop_variety: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sowing_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # PostGIS MULTIPOLYGON (SRID 4326 - WGS84)
    boundary: Mapped[Any] = mapped_column(
        Geometry("MULTIPOLYGON", srid=4326, spatial_index=False),
        nullable=False,
    )
    area_hectares: Mapped[float] = mapped_column(Float, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="farms")
    zones: Mapped[List["FarmZone"]] = relationship(
        "FarmZone",
        back_populates="farm",
        cascade="all, delete-orphan",
        order_by="FarmZone.zone_name",
    )
    observations: Mapped[List["Observation"]] = relationship(
        "Observation",
        back_populates="farm",
        passive_deletes=True,
    )
    recommendations: Mapped[List["Recommendation"]] = relationship(
        "Recommendation",
        back_populates="farm",
        passive_deletes=True,
    )
    irrigation_events: Mapped[List["IrrigationEvent"]] = relationship(
        "IrrigationEvent",
        back_populates="farm",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("idx_farms_boundary", "boundary", postgresql_using="gist"),
        Index("ix_farms_owner_created", "owner_id", "created_at"),
        Index("ix_farms_crop_type", "crop_type"),
    )

    def __repr__(self) -> str:
        return f"<Farm id={self.id} name='{self.name}' crop_type='{self.crop_type}' area={self.area_hectares}ha>"


class FarmZone(Base):
    """Sub-divided management zone within a Farm with a PostGIS Polygon boundary."""

    __tablename__ = "farm_zones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("farms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    zone_name: Mapped[str] = mapped_column(String(255), nullable=False)
    zone_code: Mapped[str] = mapped_column(String(50), nullable=False)

    # PostGIS POLYGON (SRID 4326 - WGS84)
    boundary: Mapped[Any] = mapped_column(
        Geometry("POLYGON", srid=4326, spatial_index=False),
        nullable=False,
    )
    area_hectares: Mapped[float] = mapped_column(Float, nullable=False)

    # Mapped to database column 'metadata' with JSONB
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        server_default="{}",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    farm: Mapped["Farm"] = relationship("Farm", back_populates="zones")
    observations: Mapped[List["Observation"]] = relationship(
        "Observation",
        back_populates="zone",
        passive_deletes=True,
    )
    recommendations: Mapped[List["Recommendation"]] = relationship(
        "Recommendation",
        back_populates="zone",
        passive_deletes=True,
    )
    irrigation_events: Mapped[List["IrrigationEvent"]] = relationship(
        "IrrigationEvent",
        back_populates="zone",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint("farm_id", "zone_code", name="uq_farm_zones_farm_code"),
        Index("idx_farm_zones_boundary", "boundary", postgresql_using="gist"),
        Index("ix_farm_zones_farm_zone_code", "farm_id", "zone_code"),
    )

    def __repr__(self) -> str:
        return f"<FarmZone id={self.id} farm_id={self.farm_id} code='{self.zone_code}' name='{self.zone_name}'>"
