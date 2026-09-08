"""Authentication endpoints: register, login, refresh, logout, me, change password."""

from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.errors import api_error
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.token import RevokedToken
from app.models.user import User, UserRole
from app.schemas.common import Message
from app.schemas.user import (
    AuthResponse,
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    TokenPair,
    UserCreate,
    UserRead,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_tokens(db: Session, user: User) -> TokenPair:
    """Mint an access + refresh pair for a user."""
    access = create_access_token(user.id, user.role.value)
    refresh, _, _ = create_refresh_token(user.id, user.role.value)
    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> AuthResponse:
    """Create a customer account and sign the new user in."""
    existing = db.execute(
        select(User).where(
            (User.username == payload.username) | (User.email == str(payload.email))
        )
    ).scalar_one_or_none()

    if existing is not None:
        field = "username" if existing.username == payload.username else "email"
        raise api_error(
            status.HTTP_409_CONFLICT,
            "already_registered",
            f"That {field} is already registered",
            field=field,
        )

    user = User(
        username=payload.username,
        email=str(payload.email),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=UserRole.CUSTOMER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    tokens = _issue_tokens(db, user)
    return AuthResponse(**tokens.model_dump(), user=UserRead.model_validate(user))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Exchange username + password for a token pair."""
    user = db.execute(
        select(User).where(User.username == payload.username)
    ).scalar_one_or_none()

    # Same message for unknown user and wrong password: no account enumeration.
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise api_error(
            status.HTTP_401_UNAUTHORIZED,
            "invalid_credentials",
            "Incorrect username or password",
        )
    if not user.is_active:
        raise api_error(
            status.HTTP_403_FORBIDDEN, "account_disabled", "This account is disabled"
        )

    tokens = _issue_tokens(db, user)
    return AuthResponse(**tokens.model_dump(), user=UserRead.model_validate(user))


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    """Swap a valid refresh token for a fresh token pair."""
    try:
        claims = decode_token(payload.refresh_token, expected_type="refresh")
    except jwt.ExpiredSignatureError:
        raise api_error(
            status.HTTP_401_UNAUTHORIZED, "token_expired", "Refresh token has expired"
        )
    except jwt.PyJWTError:
        raise api_error(
            status.HTTP_401_UNAUTHORIZED, "invalid_token", "Refresh token is invalid"
        )

    jti = claims.get("jti", "")
    revoked = db.execute(
        select(RevokedToken).where(RevokedToken.jti == jti)
    ).scalar_one_or_none()
    if revoked is not None:
        raise api_error(
            status.HTTP_401_UNAUTHORIZED, "token_revoked", "Refresh token has been revoked"
        )

    user = db.get(User, int(claims["sub"]))
    if user is None or not user.is_active:
        raise api_error(
            status.HTTP_401_UNAUTHORIZED, "invalid_token", "Refresh token is invalid"
        )

    return _issue_tokens(db, user)


@router.post("/logout", response_model=Message)
def logout(payload: RefreshRequest, db: Session = Depends(get_db)) -> Message:
    """Revoke a refresh token so it can no longer be exchanged."""
    try:
        claims = decode_token(payload.refresh_token, expected_type="refresh")
    except jwt.PyJWTError:
        # Nothing to revoke; treat as success so logout is always safe to call.
        return Message(message="Logged out")

    jti = claims.get("jti", "")
    already = db.execute(
        select(RevokedToken).where(RevokedToken.jti == jti)
    ).scalar_one_or_none()
    if already is None:
        db.add(
            RevokedToken(
                jti=jti,
                user_id=int(claims["sub"]),
                expires_at=datetime.fromtimestamp(int(claims["exp"]), tz=timezone.utc),
            )
        )
        db.commit()
    return Message(message="Logged out")


@router.get("/me", response_model=UserRead)
def read_me(current_user: User = Depends(get_current_user)) -> UserRead:
    """Return the signed-in user."""
    return UserRead.model_validate(current_user)


@router.post("/change-password", response_model=Message)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Message:
    """Change the signed-in user's password."""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_credentials",
            "Current password is incorrect",
            field="current_password",
        )
    if payload.current_password == payload.new_password:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "password_unchanged",
            "New password must differ from the current one",
            field="new_password",
        )

    current_user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return Message(message="Password updated")
