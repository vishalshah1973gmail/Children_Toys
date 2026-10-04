"""Find ToyBox products mentioned in a chat reply so the widget can show live cards."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.product import Product

MAX_PRODUCT_CARDS = 3
MIN_ALIAS_LENGTH = 6  # shorter names would match inside ordinary words

_PARENTHETICAL = re.compile(r"\s*\([^)]*\)\s*$")
_PUNCTUATION = str.maketrans(
    {
        "‘": "'",  # left single quotation mark
        "’": "'",  # right single quotation mark
        "“": '"',  # left double quotation mark
        "”": '"',  # right double quotation mark
        "–": "-",  # en dash
        "—": "-",  # em dash
    }
)


def _normalise(text: str) -> str:
    return text.translate(_PUNCTUATION).lower()


def _aliases(name: str) -> set[str]:
    """The full name and the name without a trailing '(100 pieces)'-style note."""
    full = _normalise(name).strip()
    short = _PARENTHETICAL.sub("", full).strip()
    return {alias for alias in (full, short) if len(alias) >= MIN_ALIAS_LENGTH}


def find_mentioned_products(db: Session, reply: str) -> list[Product]:
    """Active products named in the reply, in order of first appearance (at most 3)."""
    haystack = _normalise(reply)
    rows = db.execute(select(Product.id, Product.name).where(Product.is_active.is_(True))).all()
    candidates = [(alias, product_id) for product_id, name in rows for alias in _aliases(name)]
    # Longest first, so "Marble Run Set Deluxe" claims its text before "Marble Run Set" can.
    candidates.sort(key=lambda item: len(item[0]), reverse=True)

    claimed: list[tuple[int, int]] = []
    first_seen: dict[int, int] = {}
    for alias, product_id in candidates:
        for match in re.finditer(rf"(?<!\w){re.escape(alias)}(?!\w)", haystack):
            start, end = match.span()
            if any(start < other_end and other_start < end for other_start, other_end in claimed):
                continue
            claimed.append((start, end))
            first_seen[product_id] = min(start, first_seen.get(product_id, start))

    ordered_ids = [
        product_id for product_id, _ in sorted(first_seen.items(), key=lambda item: item[1])
    ][:MAX_PRODUCT_CARDS]
    if not ordered_ids:
        return []

    products = db.scalars(
        select(Product)
        .where(Product.id.in_(ordered_ids))
        .options(selectinload(Product.images), selectinload(Product.category))
    ).all()
    by_id = {product.id: product for product in products}
    return [by_id[product_id] for product_id in ordered_ids]
