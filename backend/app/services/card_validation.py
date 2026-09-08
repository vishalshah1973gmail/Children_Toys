"""Card-field validation. Pure functions: no I/O, no DB, no Stripe.

Only ever handles a card number/CVV in memory to validate it — nothing here
persists them. Callers must discard the raw values after this returns.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date

_DIGITS_ONLY = re.compile(r"[^0-9]")

_BRAND_RULES: dict[str, tuple[tuple[str, ...], tuple[int, ...]]] = {
    "visa": (("4",), (13, 16, 19)),
    "mastercard": (
        tuple(str(prefix) for prefix in range(51, 56))
        + tuple(str(prefix) for prefix in range(2221, 2721)),
        (16,),
    ),
    "discover": (("6011", "65") + tuple(str(prefix) for prefix in range(644, 650)), (16,)),
    "amex": (("34", "37"), (15,)),
}


@dataclass(frozen=True)
class FieldError:
    """One validation failure, tied to the input field that caused it."""

    field: str
    message: str


def _clean_number(number: str) -> str:
    return _DIGITS_ONLY.sub("", number)


def detect_brand(number: str) -> str | None:
    """Guess the card network from the number's prefix and length."""
    digits = _clean_number(number)
    for brand, (prefixes, lengths) in _BRAND_RULES.items():
        if len(digits) not in lengths:
            continue
        if any(digits.startswith(prefix) for prefix in prefixes):
            return brand
    return None


def luhn_is_valid(number: str) -> bool:
    """Standard mod-10 checksum."""
    digits = [int(char) for char in _clean_number(number)]
    if not digits:
        return False
    checksum = 0
    for index, digit in enumerate(reversed(digits)):
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def cvv_length_for(brand: str) -> int:
    """American Express uses a 4-digit CVV; every other network uses 3."""
    return 4 if brand == "amex" else 3


def validate_card(
    *,
    brand: str,
    number: str,
    exp_month: int,
    exp_year: int,
    cvv: str,
    postal_code: str,
    today: date,
) -> list[FieldError]:
    """Run every check and return every failure (not just the first)."""
    errors: list[FieldError] = []
    digits = _clean_number(number)

    if len(digits) < 12 or len(digits) > 19:
        errors.append(FieldError("number", "Card number length looks wrong."))
    elif not luhn_is_valid(digits):
        errors.append(FieldError("number", "Card number failed the checksum check."))
    elif detect_brand(digits) != brand:
        errors.append(
            FieldError("number", f"That number doesn't look like a {brand} card.")
        )

    if exp_month < 1 or exp_month > 12:
        errors.append(FieldError("exp_month", "Expiry month must be between 1 and 12."))
    else:
        last_day = calendar.monthrange(exp_year, exp_month)[1]
        expiry = date(exp_year, exp_month, last_day)
        if expiry < today:
            errors.append(FieldError("exp_year", "This card has already expired."))

    cvv_digits = _DIGITS_ONLY.sub("", cvv)
    if len(cvv_digits) != cvv_length_for(brand):
        errors.append(
            FieldError("cvv", f"{brand.title()} security codes are {cvv_length_for(brand)} digits.")
        )

    if not re.fullmatch(r"\d{5}(-\d{4})?", postal_code):
        errors.append(FieldError("postal_code", "Zip code must be 5 digits (optionally +4)."))

    return errors
