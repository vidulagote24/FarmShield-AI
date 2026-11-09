"""SQLAlchemy models registry for FarmShield AI.

All declarative models are exposed here for Alembic migration discovery and ORM relationships.
"""

from app.db.base import Base
from app.models.farm import Farm, FarmZone
from app.models.irrigation import IrrigationEvent
from app.models.observation import Observation
from app.models.recommendation import Recommendation
from app.models.user import FarmerProfile, User

__all__ = [
    "Base",
    "User",
    "FarmerProfile",
    "Farm",
    "FarmZone",
    "Observation",
    "Recommendation",
    "IrrigationEvent",
]
