"""SQLAlchemy 2.x Declarative Base and GeoAlchemy2 spatial integration foundation."""

from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass
# GeoAlchemy2 spatial types imported to prepare for spatial models (farm boundaries, fields)
try:
    from geoalchemy2 import Geometry, Geography
except ImportError:
    Geometry = None  # type: ignore
    Geography = None  # type: ignore


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models in FarmShield AI.

    Subclasses inherit SQLAlchemy 2.x mapped column support and GeoAlchemy2
    spatial data typing (e.g. Geometry('POLYGON', srid=4326)).
    """
    pass


__all__ = ["Base", "Geometry", "Geography"]
