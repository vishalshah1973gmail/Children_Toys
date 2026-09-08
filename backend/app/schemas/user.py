"""User, authentication and token schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole


class UserBase(BaseModel):
    """Fields common to user input."""

    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=120)


class UserCreate(UserBase):
    """Registration payload."""

    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def _password_strength(cls, value: str) -> str:
        if not any(character.isalpha() for character in value):
            raise ValueError("Password must contain at least one letter")
        if not any(character.isdigit() for character in value):
            raise ValueError("Password must contain at least one digit")
        return value


class UserRead(BaseModel):
    """User as returned by the API. Never contains the password hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    full_name: str | None = None
    role: UserRole
    is_active: bool
    created_at: datetime


class LoginRequest(BaseModel):
    """Username + password login payload."""

    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    """Refresh token exchange payload."""

    refresh_token: str = Field(..., min_length=10)


class ChangePasswordRequest(BaseModel):
    """Password change payload for the signed-in user."""

    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _password_strength(cls, value: str) -> str:
        if not any(character.isalpha() for character in value):
            raise ValueError("Password must contain at least one letter")
        if not any(character.isdigit() for character in value):
            raise ValueError("Password must contain at least one digit")
        return value


class TokenPair(BaseModel):
    """Access + refresh token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthResponse(TokenPair):
    """Token pair plus the authenticated user."""

    user: UserRead
