"""Pydantic schemas for Authentication, Registration, and JWT Tokens."""

import uuid
from typing import Optional
from pydantic import EmailStr, Field
from app.schemas.common import BaseSchema
from app.schemas.user import UserResponse


class UserRegisterRequest(BaseSchema):
    """Payload for public farmer registration.

    Note: The 'role' field cannot be set by public clients; it is always enforced as 'farmer'.
    """

    full_name: str = Field(..., min_length=1, max_length=255, description="Farmer's full name")
    email: EmailStr = Field(..., description="Unique email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Plaintext password meeting complexity criteria (min 8 chars, 1 letter, 1 number/symbol)",
    )
    phone: Optional[str] = Field(None, max_length=50, description="Contact phone number")
    preferred_language: Optional[str] = Field("en", max_length=50, description="Preferred language code (e.g., 'mr', 'hi', 'en')")
    village: Optional[str] = Field(None, max_length=100)
    district: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field("India", max_length=100)


class LoginRequest(BaseSchema):
    """Payload for JSON-based login."""

    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., min_length=1, max_length=128, description="User password")


class TokenResponse(BaseSchema):
    """OAuth2-compatible access token response."""

    access_token: str = Field(..., description="JWT Bearer access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token validity duration in seconds")
    user: UserResponse = Field(..., description="Public safe user profile")


class TokenPayload(BaseSchema):
    """Internal representation of decoded JWT claims."""

    sub: str
    role: str
    type: str = "access"
    email: Optional[str] = None
    exp: int
    iat: int
    iss: str
    aud: str
