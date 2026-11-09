"""Business service layer for Users and Farmer Profiles."""

import uuid
from typing import Optional
from sqlalchemy.orm import Session
from app.core.exceptions import AppException
from app.core.security import hash_password
from app.models.user import FarmerProfile, User
from app.schemas.user import (
    FarmerProfileCreate,
    FarmerProfileUpdate,
    UserCreate,
    UserUpdate,
)


class DuplicateEmailError(AppException):
    """Raised when an email address is already registered."""

    def __init__(self, email: str) -> None:
        super().__init__(
            message=f"A user with email '{email}' is already registered.",
            status_code=409,
            details={"email": email},
        )


def create_user(db: Session, user_in: UserCreate) -> User:
    """Create a new user with hashed password."""
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise DuplicateEmailError(user_in.email)

    hashed_pw = hash_password(user_in.password) if user_in.password else None
    user = User(
        full_name=user_in.full_name,
        email=user_in.email,
        phone=user_in.phone,
        hashed_password=hashed_pw,
        role=user_in.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
    """Retrieve user by UUID."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Retrieve user by email address."""
    return db.query(User).filter(User.email == email.strip().lower()).first()


def update_user(db: Session, user: User, user_in: UserUpdate) -> User:
    """Update user attributes."""
    if user_in.email and user_in.email != user.email:
        existing = db.query(User).filter(User.email == user_in.email).first()
        if existing and existing.id != user.id:
            raise DuplicateEmailError(user_in.email)
        user.email = user_in.email

    if user_in.full_name is not None:
        user.full_name = user_in.full_name
    if user_in.phone is not None:
        user.phone = user_in.phone
    if user_in.role is not None:
        user.role = user_in.role
    if user_in.is_active is not None:
        user.is_active = user_in.is_active

    db.commit()
    db.refresh(user)
    return user


def get_farmer_profile(db: Session, user_id: uuid.UUID) -> Optional[FarmerProfile]:
    """Retrieve farmer profile by user_id."""
    return db.query(FarmerProfile).filter(FarmerProfile.user_id == user_id).first()


def create_or_update_farmer_profile(
    db: Session,
    user_id: uuid.UUID,
    profile_in: FarmerProfileCreate | FarmerProfileUpdate,
) -> FarmerProfile:
    """Create or update a farmer profile linked to a user."""
    profile = get_farmer_profile(db, user_id)
    if profile:
        # Update existing profile
        update_data = profile_in.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            if val is not None:
                setattr(profile, key, val)
    else:
        # Create new profile
        create_data = profile_in.model_dump(exclude_unset=True)
        profile = FarmerProfile(user_id=user_id, **create_data)
        db.add(profile)

    db.commit()
    db.refresh(profile)
    return profile
