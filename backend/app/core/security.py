"""Password hashing and JWT issuing / decoding.

Plaintext passwords are never stored and never logged.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Literal

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TokenType = Literal["access", "refresh"]


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash of the given password."""
    # bcrypt only consumes the first 72 bytes; truncate explicitly so long
    # passwords raise no backend error.
    return pwd_context.hash(plain_password[:72])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a password against its bcrypt hash."""
    try:
        return pwd_context.verify(plain_password[:72], hashed_password)
    except ValueError:
        return False


def _create_token(
    subject: int,
    role: str,
    token_type: TokenType,
    expires_delta: timedelta,
) -> tuple[str, str, datetime]:
    """Build a signed JWT. Returns (token, jti, expiry)."""
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    jti = uuid.uuid4().hex
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "type": token_type,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, jti, expire


def create_access_token(subject: int, role: str) -> str:
    """Issue a short-lived access token."""
    token, _, _ = _create_token(
        subject, role, "access", timedelta(minutes=settings.access_token_expire_minutes)
    )
    return token


def create_refresh_token(subject: int, role: str) -> tuple[str, str, datetime]:
    """Issue a long-lived refresh token. Returns (token, jti, expiry)."""
    return _create_token(
        subject, role, "refresh", timedelta(days=settings.refresh_token_expire_days)
    )


def decode_token(token: str, expected_type: TokenType | None = None) -> Dict[str, Any]:
    """Decode and validate a JWT, raising jwt exceptions on failure."""
    payload = jwt.decode(
        token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
    if expected_type is not None and payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"Expected a {expected_type} token")
    return payload
