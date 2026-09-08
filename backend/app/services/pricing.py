"""Money maths. Every amount is an integer number of cents."""

from app.core.config import settings


def shipping_for(subtotal_cents: int) -> int:
    """Flat shipping, free above the configured threshold."""
    if subtotal_cents <= 0:
        return 0
    if subtotal_cents >= settings.free_shipping_threshold_cents:
        return 0
    return settings.shipping_flat_cents


def tax_for(subtotal_cents: int) -> int:
    """Sales tax computed from basis points, rounded half up."""
    if subtotal_cents <= 0:
        return 0
    return (subtotal_cents * settings.tax_rate_bps + 5_000) // 10_000


def totals_for(subtotal_cents: int) -> dict[str, int]:
    """Return subtotal / shipping / tax / total for a cart subtotal."""
    shipping = shipping_for(subtotal_cents)
    tax = tax_for(subtotal_cents)
    return {
        "subtotal_cents": subtotal_cents,
        "shipping_cents": shipping,
        "tax_cents": tax,
        "total_cents": subtotal_cents + shipping + tax,
    }
