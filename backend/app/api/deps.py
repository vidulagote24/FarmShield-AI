"""FastAPI dependencies for FarmShield AI: database sessions, JWT authentication, and authorization."""

import uuid
from typing import Generator, Optional
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import InvalidTokenError, decode_access_token
from app.db.session import SessionLocal
from app.models.farm import Farm
from app.models.user import User

# OAuth2 scheme configured for OpenAPI / Swagger UI interactive authorization
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False,
    description="JWT Bearer Token obtained from /api/v1/auth/login",
)


def get_db() -> Generator[Session, None, None]:
    """Dependency that yields an active database session and guarantees closure.

    Yields:
        Session: SQLAlchemy database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """Dependency for resolving authenticated user from cryptographically verified JWT.

    Fails closed (HTTP 401 Unauthorized) when an invalid, expired, or missing
    token is supplied. In tests, this dependency can be overridden via:
    `app.dependency_overrides[get_current_user] = lambda: test_user`.

    Returns:
        User: Database model representing authenticated user.

    Raises:
        HTTPException: 401 Unauthorized if token is missing, invalid, or expired.
    """
    # 1. Dev/Testing header override (explicit user resolution)
    if x_user_id and settings.DEBUG:
        try:
            target_uuid = uuid.UUID(x_user_id)
            user = db.query(User).filter(User.id == target_uuid).first()
            if user:
                return user
        except (ValueError, TypeError):
            pass

    # 2. Extract bearer token from OAuth2 scheme or Authorization header
    bearer_token = token
    if not bearer_token and authorization:
        if authorization.lower().startswith("bearer "):
            bearer_token = authorization[7:].strip()

    if not bearer_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided or are invalid.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Dev fallback for raw UUID test tokens
    if settings.DEBUG:
        try:
            raw_uuid = uuid.UUID(bearer_token)
            user = db.query(User).filter(User.id == raw_uuid).first()
            if user:
                return user
        except (ValueError, TypeError):
            pass

    # 4. Cryptographic JWT decoding and claim validation
    try:
        payload = decode_access_token(bearer_token)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims: subject missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_uuid = uuid.UUID(sub)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims: subject must be a valid UUID.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account associated with this token was not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure the authenticated user account is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account.",
        )
    return current_user


def get_current_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Ensure the authenticated user has administrative privileges."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires administrative privileges.",
        )
    return current_user


def check_farm_ownership(farm: Farm, current_user: User) -> None:
    """Ensure the authenticated user is either an admin or the owner of the target farm.

    Args:
        farm: Farm model instance.
        current_user: Currently authenticated user.

    Raises:
        HTTPException: 403 Forbidden if not authorized.
    """
    if current_user.role == "admin":
        return
    if farm.owner_id == current_user.id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to access or modify this farm resource.",
    )


def check_user_access(target_user_id: uuid.UUID, current_user: User) -> None:
    """Ensure the authenticated user is either an admin or modifying their own profile.

    Args:
        target_user_id: UUID of user to be inspected or modified.
        current_user: Currently authenticated user.

    Raises:
        HTTPException: 403 Forbidden if not authorized.
    """
    if current_user.role == "admin":
        return
    if current_user.id == target_user_id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to access or modify another user's profile.",
    )
