"""Card validation: brand detection, Luhn, expiry, CVV length, mismatches."""

from datetime import date

from app.services.card_validation import (
    cvv_length_for,
    detect_brand,
    luhn_is_valid,
    validate_card,
)

VISA = "4242424242424242"
MASTERCARD = "5555555555554444"
DISCOVER = "6011111111111117"
AMEX = "378282246310005"


def test_detect_brand_recognises_each_network() -> None:
    assert detect_brand(VISA) == "visa"
    assert detect_brand(MASTERCARD) == "mastercard"
    assert detect_brand(DISCOVER) == "discover"
    assert detect_brand(AMEX) == "amex"


def test_detect_brand_returns_none_for_unknown_prefix() -> None:
    assert detect_brand("1234567890123456") is None


def test_luhn_accepts_known_valid_numbers() -> None:
    assert luhn_is_valid(VISA) is True
    assert luhn_is_valid(AMEX) is True


def test_luhn_rejects_a_broken_checksum() -> None:
    assert luhn_is_valid("4242424242424241") is False


def test_cvv_length_is_four_for_amex_three_otherwise() -> None:
    assert cvv_length_for("amex") == 4
    assert cvv_length_for("visa") == 3
    assert cvv_length_for("mastercard") == 3
    assert cvv_length_for("discover") == 3


def test_validate_card_accepts_a_good_visa() -> None:
    errors = validate_card(
        brand="visa", number=VISA, exp_month=12, exp_year=2030,
        cvv="123", postal_code="08872", today=date(2026, 9, 8),
    )
    assert errors == []


def test_validate_card_rejects_brand_number_mismatch() -> None:
    errors = validate_card(
        brand="mastercard", number=VISA, exp_month=12, exp_year=2030,
        cvv="123", postal_code="08872", today=date(2026, 9, 8),
    )
    assert any(error.field == "number" for error in errors)


def test_validate_card_rejects_a_failed_luhn_check() -> None:
    errors = validate_card(
        brand="visa", number="4242424242424241", exp_month=12, exp_year=2030,
        cvv="123", postal_code="08872", today=date(2026, 9, 8),
    )
    assert any(error.field == "number" for error in errors)


def test_validate_card_rejects_an_expired_card() -> None:
    errors = validate_card(
        brand="visa", number=VISA, exp_month=1, exp_year=2020,
        cvv="123", postal_code="08872", today=date(2026, 9, 8),
    )
    assert any(error.field == "exp_year" for error in errors)


def test_validate_card_rejects_wrong_cvv_length_for_brand() -> None:
    errors = validate_card(
        brand="amex", number=AMEX, exp_month=12, exp_year=2030,
        cvv="123", postal_code="08872", today=date(2026, 9, 8),
    )
    assert any(error.field == "cvv" for error in errors)


def test_validate_card_strips_spaces_and_dashes_from_number() -> None:
    spaced = "4242 4242 4242 4242"
    errors = validate_card(
        brand="visa", number=spaced, exp_month=12, exp_year=2030,
        cvv="123", postal_code="08872", today=date(2026, 9, 8),
    )
    assert errors == []


def test_validate_card_collects_every_failure_not_just_the_first() -> None:
    errors = validate_card(
        brand="visa", number="0000000000000000", exp_month=1, exp_year=2020,
        cvv="1", postal_code="08872", today=date(2026, 9, 8),
    )
    fields = {error.field for error in errors}
    assert {"number", "exp_year", "cvv"}.issubset(fields)
