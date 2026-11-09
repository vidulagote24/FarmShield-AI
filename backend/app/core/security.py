"""Security, cryptography, password hashing, and JWT token management for FarmShield AI.

Features:
- Primary password hashing with Argon2id (RFC 9106)
- Backward-compatible verification for legacy PBKDF2-HMAC-SHA256 hashes
- Transparent rehashing to Argon2id upon successful authentication
- Cryptographically secure JWT access tokens (PyJWT) with strict claim validation
- Password length and complexity validation
"""

import hashlib
import hmac
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
import argon2
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerifyMismatchError
import jwt
from app.core.config import settings

# Argon2id password hasher configuration (OWASP recommended parameters)
_argon2_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MB
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)

# Legacy PBKDF2 parameters for backward compatibility
PBKDF2_ITERATIONS = 100_000


class PasswordValidationError(ValueError):
    """Raised when a plaintext password does not satisfy security complexity requirements."""
    pass


class InvalidTokenError(Exception):
    """Raised when a JWT token is invalid, expired, or malformed."""
    pass


def validate_password_complexity(password: str) -> None:
    """Validate that a candidate password meets security complexity rules.

    Requirements:
    - Minimum 8 characters, maximum 128 characters.
    - At least one letter (a-z or A-Z).
    - At least one digit (0-9) or special symbol.

    Raises:
        PasswordValidationError: If password fails length or complexity criteria.
    """
    if not password:
        raise PasswordValidationError("Password cannot be empty.")
    if len(password) < 8:
        raise PasswordValidationError("Password must contain at least 8 characters.")
    if len(password) > 128:
        raise PasswordValidationError("Password must not exceed 128 characters.")
    if not re.search(r"[A-Za-z]", password):
        raise PasswordValidationError("Password must contain at least one letter.")
    if not re.search(r"[\d!@#$%^&*(),.?\":{}|<>\-_]", password):
        raise PasswordValidationError(
            "Password must contain at least one number or special character."
        )


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id.

    Args:
        password: Raw plaintext password string.

    Returns:
        str: Encoded Argon2id hash string ($argon2id$v=19$m=65536,t=3,p=4$...).
    """
    validate_password_complexity(password)
    return _argon2_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2id or legacy PBKDF2 hash.

    Args:
        plain_password: The candidate plaintext password.
        hashed_password: The stored formatted hash string.

    Returns:
        bool: True if password matches, False otherwise.
    """
    if not plain_password or not hashed_password:
        return False

    # 1. Primary: Argon2id verification
    if hashed_password.startswith("$argon2"):
        try:
            return _argon2_hasher.verify(hashed_password, plain_password)
        except (VerifyMismatchError, InvalidHashError):
            return False
        except Exception:
            return False

    # 2. Legacy fallback: PBKDF2-HMAC-SHA256 verification
    if hashed_password.startswith("pbkdf2_sha256$"):
        try:
            parts = hashed_password.split("$")
            if len(parts) != 4:
                return False
            iterations = int(parts[1])
            salt = bytes.fromhex(parts[2])
            expected_key = bytes.fromhex(parts[3])
            calculated_key = hashlib.pbkdf2_hmac(
                "sha256", plain_password.encode("utf-8"), salt, iterations
            )
            return hmac.compare_digest(expected_key, calculated_key)
        except Exception:
            return False

    return False


def needs_rehash(hashed_password: str) -> bool:
    """Check if a password hash should be upgraded to modern Argon2id parameters.

    Returns:
        bool: True if the hash is legacy PBKDF2 or does not match current Argon2 parameters.
    """
    if not hashed_password or not hashed_password.startswith("$argon2"):
        return True
    try:
        return _argon2_hasher.check_needs_rehash(hashed_password)
    except Exception:
        return True


# Alias matching standard conventions
get_password_hash = hash_password


def create_access_token(
    subject: Union[str, uuid.UUID],
    role: str,
    email: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate a signed JWT access token with standard RFC 7519 claims.

    Args:
        subject: User primary key (UUID or string).
        role: User role ('farmer' or 'admin').
        email: User email address.
        expires_delta: Optional custom lifetime duration.
        extra_claims: Optional additional payload dictionary.

    Returns:
        str: Encoded JWT bearer token string.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "type": "access",
        "iat": now,
        "nbf": now,
        "exp": expire,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }

    if email:
        payload["email"] = email

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and cryptographically verify a JWT access token.

    Args:
        token: Raw bearer token string.

    Returns:
        dict: Validated token payload dictionary.

    Raises:
        InvalidTokenError: If token is expired, invalid, forged, or missing claims.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            options={
                "require": ["exp", "iat", "sub", "iss", "aud"],
                "verify_exp": True,
                "verify_iat": True,
                "verify_iss": True,
                "verify_aud": True,
            },
        )
    except jwt.ExpiredSignatureError as exc:
        raise InvalidTokenError("Access token has expired.") from exc
    except jwt.InvalidSignatureError as exc:
        raise InvalidTokenError("Token signature verification failed.") from exc
    except jwt.InvalidIssuerError as exc:
        raise InvalidTokenError("Token issuer is invalid.") from exc
    except jwt.InvalidAudienceError as exc:
        raise InvalidTokenError("Token audience is invalid.") from exc
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(f"Could not validate token: {exc}") from exc
    except Exception as exc:
        raise InvalidTokenError(f"Malformed token: {exc}") from exc

    if payload.get("type") != "access":
        raise InvalidTokenError("Invalid token type: expected access token.")

    return payload
