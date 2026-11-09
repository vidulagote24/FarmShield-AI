"""Authentication endpoints for FarmShield AI: registration, login, current identity, and logout."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.api.deps import get_current_active_user, get_db
from app.core.config import settings
from app.core.logging import logger
from app.core.security import (
    PasswordValidationError,
    create_access_token,
    hash_password,
    needs_rehash,
    validate_password_complexity,
    verify_password,
)
from app.models.user import FarmerProfile, User
from app.schemas.auth import LoginRequest, TokenResponse, UserRegisterRequest
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication & Access Tokens"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new farmer",
    description="Registers a new farmer user account and optional geographic profile. Role is strictly assigned as 'farmer'.",
)
def register_farmer(
    register_in: UserRegisterRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Public farmer registration endpoint.

    Enforces password complexity, prevents duplicate emails, and guarantees
    the 'farmer' role to prevent privilege escalation.
    """
    # 1. Validate password complexity
    try:
        validate_password_complexity(register_in.password)
    except PasswordValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )

    # 2. Check for duplicate email address
    normalized_email = register_in.email.strip().lower()
    existing_user = (
        db.query(User).filter(func.lower(User.email) == normalized_email).first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An account with email '{register_in.email}' is already registered.",
        )

    # 3. Hash password using Argon2id
    argon2_hash = hash_password(register_in.password)

    # 4. Create User entity (strictly role="farmer")
    user = User(
        full_name=register_in.full_name.strip(),
        email=normalized_email,
        phone=register_in.phone.strip() if register_in.phone else None,
        hashed_password=argon2_hash,
        role="farmer",
        is_active=True,
    )
    db.add(user)
    db.flush()

    # 5. Create optional FarmerProfile if location details were submitted
    if register_in.village and register_in.district and register_in.state:
        profile = FarmerProfile(
            user_id=user.id,
            preferred_language=register_in.preferred_language or "en",
            village=register_in.village,
            district=register_in.district,
            state=register_in.state,
            country=register_in.country or "India",
        )
        db.add(profile)

    db.commit()
    db.refresh(user)

    logger.info(f"Registered new farmer user {user.id} ({user.email})")
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User login and JWT token issuance",
    description="Authenticates farmer or admin via JSON or OAuth2 form data. Returns signed JWT bearer access token.",
)
async def login(
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate credentials and generate RFC 7519 JWT access token.

    Supports both JSON payloads ({"email": "...", "password": "..."}) and
    OAuth2 form-data (username="...", password="...") for Swagger UI compatibility.
    """
    email: str = ""
    password: str = ""

    content_type = request.headers.get("content-type", "")
    if (
        "application/x-www-form-urlencoded" in content_type
        or "multipart/form-data" in content_type
    ):
        form_data = await request.form()
        email = str(form_data.get("username", "")).strip().lower()
        password = str(form_data.get("password", ""))
    else:
        try:
            body = await request.json()
            email = str(body.get("email") or body.get("username", "")).strip().lower()
            password = str(body.get("password", ""))
        except Exception:
            raise HTTPException(
                status_code=422,
                detail="Request body must be valid JSON or form data.",
            )

    if not email or not password:
        raise HTTPException(
            status_code=422,
            detail="Both email and password are required.",
        )

    # 1. Retrieve user by email
    user = db.query(User).filter(func.lower(User.email) == email).first()
    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Verify password (Argon2id or backward-compatible PBKDF2)
    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Check active status
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive. Please contact support.",
        )

    # 4. Transparent migration / rehash to Argon2id if hash was legacy PBKDF2
    if needs_rehash(user.hashed_password):
        try:
            user.hashed_password = hash_password(password)
            db.commit()
            db.refresh(user)
            logger.info(f"Transparently upgraded password hash for user {user.id} to Argon2id")
        except Exception as exc:
            logger.warning(f"Could not rehash password for user {user.id}: {exc}")

    # 5. Generate JWT token
    token = create_access_token(
        subject=user.id,
        role=user.role,
        email=user.email,
    )

    expires_in_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in_seconds,
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get authenticated user profile",
    description="Returns sanitized profile details of currently authenticated user.",
)
def get_me(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """Retrieve authenticated user's profile."""
    return UserResponse.model_validate(current_user)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Log out user",
    description="Stateless token logout confirmation. Instructs client to delete JWT.",
)
def logout() -> Dict[str, str]:
    """Stateless logout endpoint."""
    return {
        "message": "Successfully logged out. Please remove the access token from client storage."
    }
