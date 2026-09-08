"""Reusable FastAPI dependencies: current user, admin guard."""

from typing import Optional

import jwt
from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import api_error
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)


def _credentials_error(message: str = "Not authenticated"):
    return api_error(status.HTTP_401_UNAUTHORIZED, "not_authenticated", message)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the signed-in user from a Bearer access token."""
    if credentials is None or not credentials.credentials:
        raise _credentials_error()

    try:
        payload = decode_token(credentials.credentials, expected_type="access")
    except jwt.ExpiredSignatureError:
        raise _credentials_error("Access token has expired")
    except jwt.PyJWTError:
        raise _credentials_error("Invalid access token")

    try:
        user_id = int(payload.get("sub", ""))
    except (TypeError, ValueError):
        raise _credentials_error("Invalid access token")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _credentials_error("User account is unavailable")
    return user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Allow only administrators through."""
    if current_user.role != UserRole.ADMIN:
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            "forbidden",
            "Administrator privileges are required for this action",
        )
    return current_user


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Return the user when a valid token is present, otherwise None."""
    if credentials is None or not credentials.credentials:
        return None
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
        return db.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        return None
