"""Application settings, loaded from environment variables / .env file."""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core
    app_name: str = "ToyBox"
    environment: str = "development"
    debug: bool = True
    api_prefix: str = "/api"

    # Database
    database_url: str = "sqlite:///./app.db"

    # Security
    jwt_secret_key: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS
    cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    # Uploads
    upload_dir: str = "static/uploads"
    max_upload_bytes: int = 5 * 1024 * 1024

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_currency: str = "usd"
    checkout_success_url: str = "http://localhost:5173/checkout/success"
    checkout_cancel_url: str = "http://localhost:5173/checkout/cancel"
    allow_dev_payment: bool = True

    # Storefront pricing
    shipping_flat_cents: int = 599
    free_shipping_threshold_cents: int = 5000
    tax_rate_bps: int = 663

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Accept a comma-separated string as well as a real list."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def stripe_enabled(self) -> bool:
        """True when a Stripe secret key is configured."""
        return bool(self.stripe_secret_key.strip())


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


settings = get_settings()
