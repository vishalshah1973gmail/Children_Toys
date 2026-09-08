"""Small shared helpers."""

import random
import re
import string
import unicodedata
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """Turn arbitrary text into a URL-safe slug."""
    normalised = unicodedata.normalize("NFKD", value)
    ascii_only = normalised.encode("ascii", "ignore").decode("ascii").lower()
    return _SLUG_STRIP.sub("-", ascii_only).strip("-") or "item"


def unique_slug(db: Session, model, base: str, exclude_id: int | None = None) -> str:
    """Return a slug unique within the given model's table."""
    candidate = slugify(base)
    suffix = 2
    while True:
        statement = select(model).where(model.slug == candidate)
        if exclude_id is not None:
            statement = statement.where(model.id != exclude_id)
        if db.execute(statement).scalar_one_or_none() is None:
            return candidate
        candidate = f"{slugify(base)}-{suffix}"
        suffix += 1


def generate_order_number(now: datetime | None = None) -> str:
    """Human-friendly order number, e.g. TB-20260114-4F7QK2."""
    moment = now or datetime.now(timezone.utc)
    tail = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"TB-{moment.strftime('%Y%m%d')}-{tail}"


def format_age_range(min_months: int, max_months: int) -> str:
    """Render an age range for display, e.g. '18 months - 4 years'."""

    def part(months: int) -> str:
        if months < 24:
            return f"{months} months"
        return f"{months // 12} years"

    return f"{part(min_months)} - {part(max_months)}"
