"""API v1 Endpoints for Users and Farmer Profiles with RBAC and Access Protection."""

import math
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api.deps import (
    check_user_access,
    get_current_active_user,
    get_current_admin,
    get_db,
)
from app.core.exceptions import EntityNotFoundError
from app.models.user import User
from app.schemas.user import (
    FarmerProfileCreate,
    FarmerProfileResponse,
    FarmerProfileUpdate,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.services import user_service

router = APIRouter(tags=["Users & Farmers"])


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
) -> User:
    """Create a new farmer user account.

    To prevent unauthorized privilege escalation, non-farmer roles cannot be created
    through this public endpoint.
    """
    if user_in.role != "farmer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public registration cannot create administrative roles. Only 'farmer' role is permitted.",
        )
    return user_service.create_user(db, user_in)


@router.get(
    "/users/me",
    response_model=UserResponse,
    summary="Get current user details",
)
def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Retrieve details for currently authenticated user."""
    return current_user


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Get user by UUID",
)
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Retrieve user details by UUID with access restriction (self or admin)."""
    check_user_access(user_id, current_user)
    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found.",
        )
    return user


@router.put(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Update user details",
)
def update_user(
    user_id: uuid.UUID,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Update user information with access restriction (self or admin)."""
    check_user_access(user_id, current_user)
    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found.",
        )
    return user_service.update_user(db, user, user_in)


@router.get(
    "/farmers/{user_id}/profile",
    response_model=FarmerProfileResponse,
    summary="Get farmer profile",
)
def get_farmer_profile(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FarmerProfileResponse:
    """Retrieve profile details for a specific farmer user with access check."""
    check_user_access(user_id, current_user)
    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found.",
        )

    profile = user_service.get_farmer_profile(db, user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farmer profile for user '{user_id}' has not been created yet.",
        )
    return profile


@router.put(
    "/farmers/{user_id}/profile",
    response_model=FarmerProfileResponse,
    summary="Create or update farmer profile",
)
def update_farmer_profile(
    user_id: uuid.UUID,
    profile_in: FarmerProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FarmerProfileResponse:
    """Create or update farmer profile information with access check."""
    check_user_access(user_id, current_user)
    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found.",
        )

    return user_service.create_or_update_farmer_profile(db, user_id, profile_in)
