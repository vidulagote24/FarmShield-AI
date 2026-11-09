"""Pydantic schemas for User and FarmerProfile entities."""

import re
import uuid
from datetime import datetime
from typing import Optional
from pydantic import Field, field_validator
from app.schemas.common import BaseSchema

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class UserBase(BaseSchema):
    """Base fields for User."""

    full_name: str = Field(..., min_length=2, max_length=255)
    email: str = Field(..., min_length=5, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    role: str = Field("farmer", max_length=50)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_REGEX.match(v):
            raise ValueError("Invalid email format.")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        role = v.strip().lower()
        if role not in ("farmer", "admin", "agronomist"):
            raise ValueError("Role must be 'farmer', 'admin', or 'agronomist'.")
        return role


class UserCreate(UserBase):
    """Payload for creating a new User."""

    password: Optional[str] = Field(None, min_length=6, max_length=128)


class UserUpdate(BaseSchema):
    """Payload for updating an existing User."""

    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[str] = Field(None, min_length=5, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    role: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().lower()
            if not EMAIL_REGEX.match(v):
                raise ValueError("Invalid email format.")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            role = v.strip().lower()
            if role not in ("farmer", "admin", "agronomist"):
                raise ValueError("Role must be 'farmer', 'admin', or 'agronomist'.")
            return role
        return v


class FarmerProfileBase(BaseSchema):
    """Base fields for FarmerProfile."""

    preferred_language: str = Field("en", max_length=50)
    village: str = Field(..., min_length=1, max_length=100)
    district: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=1, max_length=100)
    country: str = Field("India", max_length=100)


class FarmerProfileCreate(FarmerProfileBase):
    """Payload for creating a FarmerProfile."""

    pass


class FarmerProfileUpdate(BaseSchema):
    """Payload for updating a FarmerProfile."""

    preferred_language: Optional[str] = Field(None, max_length=50)
    village: Optional[str] = Field(None, max_length=100)
    district: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)


class FarmerProfileResponse(FarmerProfileBase):
    """Response representation of a FarmerProfile."""

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class UserResponse(BaseSchema):
    """Response representation of a User (strictly omitting hashed_password)."""

    id: uuid.UUID
    full_name: str
    email: str
    phone: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    farmer_profile: Optional[FarmerProfileResponse] = None
