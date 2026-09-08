# Guest Checkout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a shopper check out without an account: enter billing address + a
manually-typed card + shipping address, get a locally-simulated "payment" (no
Stripe call), see a receipt, get it emailed, and have the order stored in the DB.

**Architecture:** New `POST /api/checkout/guest` endpoint, parallel to the existing
authenticated `/api/checkout/session` (Stripe-hosted) flow, which is untouched. A
pure-function card validator gates the request; on success the order is created
already `PAID` (no pending/webhook step — nothing calls Stripe). `Order.user_id`
becomes nullable and gains billing-address columns; `Payment` gains masked
card-summary columns (brand/last4/expiry only — never the full number or CVV).

**Tech Stack:** FastAPI + SQLAlchemy + Alembic + pytest (backend, already in repo,
no new backend dependency). React + TypeScript + Zustand + axios (frontend, already
in repo, no new frontend dependency). Email via Python's stdlib `smtplib` — no new
package needed.

**Spec:** `docs/superpowers/specs/2026-09-08-guest-checkout-design.md`

## Global Constraints

- Never persist the full card number or the CVV anywhere (not in a DB column, not in
  a log line). Only `card_brand`, `card_last4`, `card_exp_month`, `card_exp_year` are
  stored.
- The guest path never calls Stripe. It is fully simulated: our own validation is
  the only gate, and a pass means the order is created `PAID` immediately.
- The existing authenticated Stripe-hosted flow (`/api/checkout/session`,
  `/api/checkout/dev-confirm/*`, `/api/webhooks/stripe`) is not modified.
- Money is always integer cents, following the existing `pricing.py` convention.
- A failed receipt email must not fail the order: the response reports
  `email_sent: false` and the exact SMTP error is logged, never swallowed silently.
- No new backend or frontend package is installed (`smtplib` is stdlib; no
  frontend test runner exists in this repo, so frontend verification is
  `tsc --noEmit` plus a manual browser walkthrough, not new unit tests).

---

## Task 1: Schema — nullable `user_id`, billing columns, card-summary columns

**Files:**
- Modify: `backend/app/models/order.py`
- Modify: `backend/app/models/payment.py`
- Create: `backend/alembic/versions/0002_guest_checkout.py`
- Modify: `backend/app/schemas/order.py` (`OrderRead.user_id` → `int | None`)

**Interfaces:**
- Produces: `Order.user_id: int | None`, `Order.billing_name/line1/line2/city/state/postal_code/country: str | None`, `Order.user: User | None`.
- Produces: `Payment.card_brand: str | None`, `Payment.card_last4: str | None`, `Payment.card_exp_month: int | None`, `Payment.card_exp_year: int | None`.

- [ ] **Step 1: Edit `backend/app/models/order.py`** — make `user_id` nullable, widen
  the relationship type, add the seven billing columns right after the existing
  `shipping_*` block:

```python
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=True
    )
```

  and change:

```python
    user: Mapped["User | None"] = relationship(back_populates="orders")
```

  and insert after `shipping_country`:

```python
    billing_name: Mapped[str | None] = mapped_column(String(120))
    billing_line1: Mapped[str | None] = mapped_column(String(200))
    billing_line2: Mapped[str | None] = mapped_column(String(200))
    billing_city: Mapped[str | None] = mapped_column(String(120))
    billing_state: Mapped[str | None] = mapped_column(String(120))
    billing_postal_code: Mapped[str | None] = mapped_column(String(20))
    billing_country: Mapped[str | None] = mapped_column(String(2))
```

- [ ] **Step 2: Edit `backend/app/models/payment.py`** — add four columns right
  after `failure_reason`:

```python
    card_brand: Mapped[str | None] = mapped_column(String(20))
    card_last4: Mapped[str | None] = mapped_column(String(4))
    card_exp_month: Mapped[int | None] = mapped_column(Integer)
    card_exp_year: Mapped[int | None] = mapped_column(Integer)
```

  (`Integer` is already imported in that file.)

- [ ] **Step 3: Edit `backend/app/schemas/order.py`** — in `OrderRead`, change
  `user_id: int` to `user_id: int | None`, and add the same seven billing fields
  (all `str | None = None`) right after `shipping_country`, matching the existing
  `shipping_*` field style.

- [ ] **Step 4: Write the migration** `backend/alembic/versions/0002_guest_checkout.py`:

```python
"""Guest checkout: nullable order.user_id, billing columns, card summary on payments.

Revision ID: 0002_guest_checkout
Revises: 0001_initial
Create Date: 2026-09-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_guest_checkout"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=True)
        batch_op.add_column(sa.Column("billing_name", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("billing_line1", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("billing_line2", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("billing_city", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("billing_state", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("billing_postal_code", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("billing_country", sa.String(length=2), nullable=True))

    op.add_column("payments", sa.Column("card_brand", sa.String(length=20), nullable=True))
    op.add_column("payments", sa.Column("card_last4", sa.String(length=4), nullable=True))
    op.add_column("payments", sa.Column("card_exp_month", sa.Integer(), nullable=True))
    op.add_column("payments", sa.Column("card_exp_year", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("payments", "card_exp_year")
    op.drop_column("payments", "card_exp_month")
    op.drop_column("payments", "card_last4")
    op.drop_column("payments", "card_brand")

    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_column("billing_country")
        batch_op.drop_column("billing_postal_code")
        batch_op.drop_column("billing_state")
        batch_op.drop_column("billing_city")
        batch_op.drop_column("billing_line2")
        batch_op.drop_column("billing_name")
        batch_op.drop_column("billing_line1")
        batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
```

- [ ] **Step 5: Apply it to the dev database and verify.**

Run: `cd backend && alembic upgrade head`
Expected: logs `Running upgrade 0001_initial -> 0002_guest_checkout`, no error.

Verify columns landed:

Run: `cd backend && python -c "import sqlite3; c = sqlite3.connect('app.db'); print([r[1] for r in c.execute('PRAGMA table_info(orders)')]); print([r[1] for r in c.execute('PRAGMA table_info(payments)')])"`
Expected: the `orders` list includes `billing_name` etc., the `payments` list
includes `card_brand` etc.

- [ ] **Step 6: Run the existing test suite to confirm nothing broke.**

Run: `cd backend && pytest -q`
Expected: all existing tests still pass (they use `Base.metadata.create_all`, which
picks up the model changes directly, independent of the migration).

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/order.py backend/app/models/payment.py backend/app/schemas/order.py backend/alembic/versions/0002_guest_checkout.py
git commit -m "feat: nullable order.user_id, billing columns, card summary on payments"
```

---

## Task 2: Card validation service

**Files:**
- Create: `backend/app/services/card_validation.py`
- Test: `backend/tests/test_card_validation.py`

**Interfaces:**
- Produces: `FieldError` (namedtuple/dataclass with `field: str`, `message: str`),
  `detect_brand(number: str) -> str | None`, `luhn_is_valid(number: str) -> bool`,
  `cvv_length_for(brand: str) -> int`,
  `validate_card(brand: str, number: str, exp_month: int, exp_year: int, cvv: str, postal_code: str, today: date) -> list[FieldError]`.
- Consumes: nothing (pure functions, no DB/network).

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/test_card_validation.py -v`
Expected: `ModuleNotFoundError: No module named 'app.services.card_validation'`

- [ ] **Step 3: Implement it**

```python
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && pytest tests/test_card_validation.py -v`
Expected: all 12 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/card_validation.py backend/tests/test_card_validation.py
git commit -m "feat: pure-function card validation (Luhn, brand, expiry, CVV length)"
```

---

## Task 3: Email settings + receipt sender

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/.env.example` (repo root `.env.example`, and add a
  `backend/.env` entry pattern — see Step 1)
- Create: `backend/app/services/email_service.py`
- Test: `backend/tests/test_email_service.py`

**Interfaces:**
- Consumes: `Order` (from Task 1, for `order.contact_email`, `order.items`,
  `order.shipping_*`, `order.total_cents`).
- Produces: `email_service.send_receipt(order: Order) -> None` (raises on any
  SMTP failure — the caller in Task 6 decides how to handle that).

- [ ] **Step 1: Add SMTP settings.** Edit `backend/app/core/config.py`, add after
  the `# Storefront pricing` block:

```python
    # Email (guest checkout receipts)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_app_password: str = ""
    email_from: str = ""
```

  Then add the same five keys (with blank values, as placeholders) to
  `backend/.env.example` so the format is documented; the real values go in
  `backend/.env` (already gitignored) and Vishal supplies them himself — do not
  invent or hardcode a real Gmail address/password anywhere.

- [ ] **Step 2: Write the failing test.** It mocks `smtplib.SMTP` so no real
  network call happens:

```python
"""Receipt email sending — mocked SMTP, no real network call."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.order import Order, OrderItem, OrderStatus
from app.services import email_service


def _sample_order() -> Order:
    order = Order(
        id=1,
        order_number="TB-20260908-ABC123",
        user_id=None,
        status=OrderStatus.PAID,
        subtotal_cents=1599,
        shipping_cents=599,
        tax_cents=106,
        total_cents=2304,
        currency="usd",
        contact_email="guest@example.com",
        shipping_name="Sam Shopper",
        shipping_line1="42 Ernston Rd",
        shipping_line2=None,
        shipping_city="Sayreville",
        shipping_state="NJ",
        shipping_postal_code="08872",
        shipping_country="US",
        placed_at=datetime.now(timezone.utc),
        paid_at=datetime.now(timezone.utc),
    )
    order.items = [
        OrderItem(
            id=1, order_id=1, product_id=1, product_name="Sunny Farm Puzzle",
            product_slug="sunny-farm-puzzle", image_url="/static/uploads/puzzle.svg",
            unit_price_cents=1599, quantity=1, line_total_cents=1599,
        )
    ]
    return order


def test_send_receipt_logs_in_and_sends_to_the_contact_email() -> None:
    order = _sample_order()
    with patch("app.services.email_service.smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        email_service.send_receipt(order)

        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.sendmail.assert_called_once()
        _, recipients, message = mock_server.sendmail.call_args[0]
        assert recipients == ["guest@example.com"]
        assert "Sunny Farm Puzzle" in message


def test_send_receipt_raises_when_smtp_fails() -> None:
    order = _sample_order()
    with patch("app.services.email_service.smtplib.SMTP") as mock_smtp_cls:
        mock_smtp_cls.return_value.__enter__.side_effect = OSError("connection refused")
        with pytest.raises(OSError):
            email_service.send_receipt(order)
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd backend && pytest tests/test_email_service.py -v`
Expected: `ModuleNotFoundError: No module named 'app.services.email_service'`

- [ ] **Step 4: Implement it**

```python
"""Guest-checkout receipt emails, sent over real SMTP (Gmail + app password).

Raises on any failure. The caller decides whether that should block the
checkout response — see routers/checkout.py, which logs and continues.
"""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings
from app.models.order import Order


def _render_html(order: Order) -> str:
    rows = "".join(
        f"<tr><td><img src='{item.image_url or ''}' width='48' /></td>"
        f"<td>{item.product_name}</td><td>x{item.quantity}</td>"
        f"<td>${item.line_total_cents / 100:.2f}</td></tr>"
        for item in order.items
    )
    address = (
        f"{order.shipping_name}<br>{order.shipping_line1}"
        + (f"<br>{order.shipping_line2}" if order.shipping_line2 else "")
        + f"<br>{order.shipping_city}, {order.shipping_state} {order.shipping_postal_code}"
    )
    return (
        f"<h2>Thanks for your order, {order.shipping_name}!</h2>"
        f"<p>Order {order.order_number}</p>"
        f"<table>{rows}</table>"
        f"<p><strong>Total: ${order.total_cents / 100:.2f}</strong></p>"
        f"<p>Shipping to:<br>{address}</p>"
    )


def send_receipt(order: Order) -> None:
    """Send the order receipt to order.contact_email. Raises on SMTP failure."""
    message = MIMEMultipart("alternative")
    message["Subject"] = f"Your ToyBox order {order.order_number}"
    message["From"] = settings.email_from or settings.smtp_user
    message["To"] = order.contact_email
    message.attach(MIMEText(_render_html(order), "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_app_password)
        server.sendmail(message["From"], [order.contact_email], message.as_string())
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd backend && pytest tests/test_email_service.py -v`
Expected: both tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/config.py backend/.env.example backend/app/services/email_service.py backend/tests/test_email_service.py
git commit -m "feat: SMTP receipt email service for guest checkout"
```

---

## Task 4: Guest checkout request/response schemas

**Files:**
- Create: `backend/app/schemas/checkout_guest.py`

**Interfaces:**
- Consumes: nothing new (plain Pydantic).
- Produces: `GuestAddress`, `CardDetails`, `GuestCheckoutItem`,
  `GuestCheckoutRequest`, `GuestCheckoutResponse` — imported by Task 6's router
  and Task 5's service.

- [ ] **Step 1: Write the file**

```python
"""Request/response shapes for the unauthenticated guest checkout endpoint."""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.schemas.order import OrderRead

CardBrand = Literal["visa", "mastercard", "discover", "amex"]


class GuestAddress(BaseModel):
    """A billing or shipping address supplied by a guest."""

    name: str = Field(..., min_length=2, max_length=120)
    line1: str = Field(..., min_length=2, max_length=200)
    line2: str | None = Field(default=None, max_length=200)
    city: str = Field(..., min_length=1, max_length=120)
    state: str = Field(..., min_length=1, max_length=120)
    postal_code: str = Field(..., min_length=3, max_length=20)
    country: str = Field(default="US", min_length=2, max_length=2)


class CardDetails(BaseModel):
    """Card fields as typed by the guest. Never stored as-is — see card_validation."""

    brand: CardBrand
    number: str = Field(..., min_length=12, max_length=23)
    name_on_card: str = Field(..., min_length=2, max_length=120)
    exp_month: int = Field(..., ge=1, le=12)
    exp_year: int = Field(..., ge=2000, le=2100)
    cvv: str = Field(..., min_length=3, max_length=4)
    postal_code: str = Field(..., min_length=5, max_length=10)


class GuestCheckoutItem(BaseModel):
    """One cart line, as tracked client-side for a guest (no server cart)."""

    product_id: int
    quantity: int = Field(..., gt=0)


class GuestCheckoutRequest(BaseModel):
    """Everything needed to place and 'pay' a guest order in one request."""

    contact_email: EmailStr
    billing_address: GuestAddress
    card: CardDetails
    same_as_billing: bool
    shipping_address: GuestAddress | None = None
    items: list[GuestCheckoutItem] = Field(..., min_length=1)


class GuestCheckoutResponse(BaseModel):
    """The placed order, for the receipt screen, plus whether the email went out."""

    order: OrderRead
    email_sent: bool
```

- [ ] **Step 2: Verify it imports cleanly**

Run: `cd backend && python -c "from app.schemas.checkout_guest import GuestCheckoutRequest; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/checkout_guest.py
git commit -m "feat: pydantic schemas for guest checkout request/response"
```

---

## Task 5: `order_service.create_guest_order`

**Files:**
- Modify: `backend/app/services/order_service.py`
- Test: `backend/tests/test_order_service_guest.py`

**Interfaces:**
- Consumes: `card_validation.validate_card` (Task 2), `pricing.totals_for`
  (existing), `GuestCheckoutRequest` (Task 4), `Order`/`OrderItem`/`Payment`
  models (Task 1).
- Produces: `order_service.create_guest_order(db: Session, payload: GuestCheckoutRequest) -> Order`
  — raises `api_error(...)` (400/409/422) on failure, otherwise returns a
  `PAID` order with items and one `Payment` row attached, not yet committed
  (caller commits — same pattern as `create_pending_order`).

- [ ] **Step 1: Write the failing tests**

```python
"""Guest order creation: pricing, stock, card gate, no Stripe involvement."""

from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.order import OrderStatus
from app.models.payment import PaymentStatus
from app.models.product import Product
from app.schemas.checkout_guest import (
    CardDetails,
    GuestAddress,
    GuestCheckoutItem,
    GuestCheckoutRequest,
)
from app.services import order_service

GOOD_CARD = CardDetails(
    brand="visa", number="4242424242424242", name_on_card="Sam Shopper",
    exp_month=12, exp_year=2030, cvv="123", postal_code="08872",
)
BILLING = GuestAddress(
    name="Sam Shopper", line1="42 Ernston Rd", city="Sayreville",
    state="NJ", postal_code="08872", country="US",
)


def _request(product_id: int, **overrides) -> GuestCheckoutRequest:
    base = dict(
        contact_email="guest@example.com",
        billing_address=BILLING,
        card=GOOD_CARD,
        same_as_billing=True,
        shipping_address=None,
        items=[GuestCheckoutItem(product_id=product_id, quantity=1)],
    )
    base.update(overrides)
    return GuestCheckoutRequest(**base)


def test_create_guest_order_marks_paid_and_decrements_stock(
    db: Session, product_factory
) -> None:
    product = product_factory(slug="guest-toy", price_cents=1599, stock=5)
    order = order_service.create_guest_order(db, _request(product.id), today=date(2026, 9, 8))
    db.commit()

    assert order.user_id is None
    assert order.status == OrderStatus.PAID
    assert order.contact_email == "guest@example.com"
    assert order.billing_name == "Sam Shopper"
    assert order.shipping_name == "Sam Shopper"  # same_as_billing copied it across
    assert order.subtotal_cents == 1599
    assert len(order.payments) == 1
    payment = order.payments[0]
    assert payment.status == PaymentStatus.SUCCEEDED
    assert payment.card_brand == "visa"
    assert payment.card_last4 == "4242"
    assert payment.provider == "guest_form"

    db.expire_all()
    assert db.get(Product, product.id).stock_quantity == 4


def test_create_guest_order_uses_explicit_shipping_when_not_same_as_billing(
    db: Session, product_factory
) -> None:
    product = product_factory(slug="guest-toy-2", price_cents=1000, stock=5)
    shipping = GuestAddress(
        name="Gift Recipient", line1="1 Other St", city="Elsewhere",
        state="NY", postal_code="10001", country="US",
    )
    order = order_service.create_guest_order(
        db, _request(product.id, same_as_billing=False, shipping_address=shipping),
        today=date(2026, 9, 8),
    )
    db.commit()
    assert order.shipping_name == "Gift Recipient"
    assert order.shipping_city == "Elsewhere"


def test_create_guest_order_rejects_empty_cart(db: Session) -> None:
    with pytest.raises(HTTPException) as excinfo:
        request = _request.__wrapped__ if False else None  # placeholder unused
    # Empty items is rejected by pydantic's min_length=1 before this function is
    # even called from the router, so exercise the service directly with a
    # constructed request that bypasses that (simulating a defensive check).


def test_create_guest_order_rejects_insufficient_stock(
    db: Session, product_factory
) -> None:
    product = product_factory(slug="guest-toy-3", price_cents=1000, stock=1)
    with pytest.raises(HTTPException) as excinfo:
        order_service.create_guest_order(
            db, _request(product.id, items=[GuestCheckoutItem(product_id=product.id, quantity=2)]),
            today=date(2026, 9, 8),
        )
    assert excinfo.value.detail["code"] == "insufficient_stock"


def test_create_guest_order_rejects_a_bad_card(db: Session, product_factory) -> None:
    product = product_factory(slug="guest-toy-4", price_cents=1000, stock=5)
    bad_card = GOOD_CARD.model_copy(update={"number": "4242424242424241"})
    with pytest.raises(HTTPException) as excinfo:
        order_service.create_guest_order(
            db, _request(product.id, card=bad_card), today=date(2026, 9, 8)
        )
    assert excinfo.value.detail["code"] == "invalid_card"
```

  Delete the placeholder `test_create_guest_order_rejects_empty_cart` body above
  before running — it was left unfinished on purpose so you notice it; replace it
  with:

```python
def test_create_guest_order_rejects_empty_cart(db: Session) -> None:
    request = GuestCheckoutRequest.model_construct(
        contact_email="guest@example.com", billing_address=BILLING, card=GOOD_CARD,
        same_as_billing=True, shipping_address=None, items=[],
    )
    with pytest.raises(HTTPException) as excinfo:
        order_service.create_guest_order(db, request, today=date(2026, 9, 8))
    assert excinfo.value.detail["code"] == "empty_cart"
```

  (`model_construct` bypasses pydantic's own `min_length=1` validation so the
  service's own defensive check is what's actually under test.)

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/test_order_service_guest.py -v`
Expected: `AttributeError: module 'app.services.order_service' has no attribute 'create_guest_order'`

- [ ] **Step 3: Implement it.** Add to `backend/app/services/order_service.py`
  (needs new imports at the top: `from datetime import date` already covered by
  existing `datetime` import — add `date` to that import line; add
  `from app.models.payment import ...` already present; add
  `from app.schemas.checkout_guest import GuestCheckoutRequest`; add
  `from app.services import card_validation`):

```python
def create_guest_order(
    db: Session,
    payload: "GuestCheckoutRequest",
    *,
    today: date | None = None,
) -> Order:
    """Create and immediately mark-paid a guest order. No Stripe call ever.

    Raises 400 (empty cart), 409 (stock), or 422 (invalid_card).
    """
    if not payload.items:
        raise api_error(status.HTTP_400_BAD_REQUEST, "empty_cart", "Your cart is empty")

    products: dict[int, Product] = {}
    for line in payload.items:
        product = db.get(Product, line.product_id)
        if product is None or not product.is_active:
            raise api_error(
                status.HTTP_409_CONFLICT, "product_unavailable",
                f"Product {line.product_id} is no longer available",
            )
        if line.quantity > product.stock_quantity:
            raise api_error(
                status.HTTP_409_CONFLICT, "insufficient_stock",
                (
                    f"Only {product.stock_quantity} of '{product.name}' left in stock "
                    f"(you asked for {line.quantity})"
                ),
                field="quantity",
            )
        products[line.product_id] = product

    card = payload.card
    card_errors = card_validation.validate_card(
        brand=card.brand, number=card.number, exp_month=card.exp_month,
        exp_year=card.exp_year, cvv=card.cvv, postal_code=card.postal_code,
        today=today or datetime.now(timezone.utc).date(),
    )
    if card_errors:
        first = card_errors[0]
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_card", first.message,
            field=first.field,
        )

    subtotal = sum(products[line.product_id].price_cents * line.quantity for line in payload.items)
    totals = totals_for(subtotal)
    now = datetime.now(timezone.utc)
    billing = payload.billing_address
    shipping = billing if payload.same_as_billing else payload.shipping_address

    order = Order(
        order_number=generate_order_number(now),
        user_id=None,
        status=OrderStatus.PAID,
        currency=settings.stripe_currency,
        contact_email=str(payload.contact_email),
        billing_name=billing.name,
        billing_line1=billing.line1,
        billing_line2=billing.line2,
        billing_city=billing.city,
        billing_state=billing.state,
        billing_postal_code=billing.postal_code,
        billing_country=billing.country.upper(),
        shipping_name=shipping.name,
        shipping_line1=shipping.line1,
        shipping_line2=shipping.line2,
        shipping_city=shipping.city,
        shipping_state=shipping.state,
        shipping_postal_code=shipping.postal_code,
        shipping_country=shipping.country.upper(),
        placed_at=now,
        paid_at=now,
        **totals,
    )

    for line in payload.items:
        product = products[line.product_id]
        order.items.append(
            OrderItem(
                product_id=product.id,
                product_name=product.name,
                product_slug=product.slug,
                image_url=product.primary_image_url,
                unit_price_cents=product.price_cents,
                quantity=line.quantity,
                line_total_cents=product.price_cents * line.quantity,
            )
        )
        product.stock_quantity -= line.quantity

    digits = "".join(char for char in card.number if char.isdigit())
    order.payments.append(
        Payment(
            provider="guest_form",
            amount_cents=totals["total_cents"],
            currency=settings.stripe_currency,
            status=PaymentStatus.SUCCEEDED,
            card_brand=card.brand,
            card_last4=digits[-4:],
            card_exp_month=card.exp_month,
            card_exp_year=card.exp_year,
        )
    )

    db.add(order)
    db.flush()
    return order
```

  Add `from app.models.product import Product` to the imports if not already
  present in that file (it currently is not — check the top of the file before
  adding, to avoid a duplicate import).

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && pytest tests/test_order_service_guest.py -v`
Expected: all 5 tests PASS.

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && pytest -q`
Expected: everything passes, including the pre-existing suite.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/order_service.py backend/tests/test_order_service_guest.py
git commit -m "feat: order_service.create_guest_order — simulated, card-validated, no Stripe"
```

---

## Task 6: `POST /api/checkout/guest` endpoint

**Files:**
- Modify: `backend/app/routers/checkout.py`
- Test: `backend/tests/test_checkout_guest_endpoint.py`

**Interfaces:**
- Consumes: `order_service.create_guest_order` (Task 5), `email_service.send_receipt`
  (Task 3), `GuestCheckoutRequest`/`GuestCheckoutResponse` (Task 4).
- Produces: the live `/api/checkout/guest` route other code (frontend) calls.

- [ ] **Step 1: Write the failing tests**

```python
"""End-to-end guest checkout: no auth header anywhere in this file."""

from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.product import Product

GOOD_PAYLOAD_BASE = {
    "contact_email": "guest@example.com",
    "billing_address": {
        "name": "Sam Shopper", "line1": "42 Ernston Rd", "city": "Sayreville",
        "state": "NJ", "postal_code": "08872", "country": "US",
    },
    "card": {
        "brand": "visa", "number": "4242424242424242", "name_on_card": "Sam Shopper",
        "exp_month": 12, "exp_year": 2030, "cvv": "123", "postal_code": "08872",
    },
    "same_as_billing": True,
}


def test_guest_checkout_happy_path_needs_no_auth(client: TestClient, product_factory) -> None:
    product = product_factory(slug="guest-endpoint-toy", price_cents=1599, stock=5)
    payload = {**GOOD_PAYLOAD_BASE, "items": [{"product_id": product.id, "quantity": 1}]}

    with patch("app.routers.checkout.email_service.send_receipt") as mock_send:
        response = client.post("/api/checkout/guest", json=payload)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["order"]["status"] == "paid"
    assert body["order"]["user_id"] is None
    assert body["email_sent"] is True
    mock_send.assert_called_once()


def test_guest_checkout_email_failure_still_returns_the_order(
    client: TestClient, product_factory
) -> None:
    product = product_factory(slug="guest-endpoint-toy-2", price_cents=1000, stock=5)
    payload = {**GOOD_PAYLOAD_BASE, "items": [{"product_id": product.id, "quantity": 1}]}

    with patch("app.routers.checkout.email_service.send_receipt", side_effect=OSError("smtp down")):
        response = client.post("/api/checkout/guest", json=payload)

    assert response.status_code == 201, response.text
    assert response.json()["email_sent"] is False


def test_guest_checkout_rejects_insufficient_stock(client: TestClient, product_factory) -> None:
    product = product_factory(slug="guest-endpoint-toy-3", price_cents=1000, stock=1)
    payload = {**GOOD_PAYLOAD_BASE, "items": [{"product_id": product.id, "quantity": 2}]}
    response = client.post("/api/checkout/guest", json=payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "insufficient_stock"


def test_guest_checkout_rejects_invalid_card(client: TestClient, product_factory) -> None:
    product = product_factory(slug="guest-endpoint-toy-4", price_cents=1000, stock=5)
    bad_card = {**GOOD_PAYLOAD_BASE["card"], "number": "4242424242424241"}
    payload = {**GOOD_PAYLOAD_BASE, "card": bad_card, "items": [{"product_id": product.id, "quantity": 1}]}
    response = client.post("/api/checkout/guest", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_card"


def test_guest_checkout_decrements_stock_and_leaves_no_pending_state(
    client: TestClient, db: Session, product_factory
) -> None:
    product = product_factory(slug="guest-endpoint-toy-5", price_cents=1000, stock=5)
    payload = {**GOOD_PAYLOAD_BASE, "items": [{"product_id": product.id, "quantity": 2}]}
    with patch("app.routers.checkout.email_service.send_receipt"):
        response = client.post("/api/checkout/guest", json=payload)
    assert response.status_code == 201
    db.expire_all()
    assert db.get(Product, product.id).stock_quantity == 3
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && pytest tests/test_checkout_guest_endpoint.py -v`
Expected: 404 (route doesn't exist yet) on every test.

- [ ] **Step 3: Implement the route.** Add to `backend/app/routers/checkout.py`
  (add `import logging` at the top if not present, and
  `from app.schemas.checkout_guest import GuestCheckoutRequest, GuestCheckoutResponse`,
  `from app.services import email_service`):

```python
logger = logging.getLogger(__name__)


@router.post(
    "/checkout/guest",
    response_model=GuestCheckoutResponse,
    status_code=status.HTTP_201_CREATED,
)
def guest_checkout(
    payload: GuestCheckoutRequest,
    db: Session = Depends(get_db),
) -> GuestCheckoutResponse:
    """Place and simulate-pay a guest order in one request. No auth, no Stripe."""
    order = order_service.create_guest_order(db, payload)
    db.commit()
    db.refresh(order)

    email_sent = True
    try:
        email_service.send_receipt(order)
    except Exception as exc:  # noqa: BLE001 - a failed email must not fail the order
        logger.warning("Guest receipt email failed for %s: %s", order.order_number, exc)
        email_sent = False

    return GuestCheckoutResponse(order=OrderRead.model_validate(order), email_sent=email_sent)
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && pytest tests/test_checkout_guest_endpoint.py -v`
Expected: all 5 tests PASS.

- [ ] **Step 5: Run the entire backend suite one more time**

Run: `cd backend && pytest -q`
Expected: full suite green, including the pre-existing Stripe-flow tests
(confirms the existing flow is untouched).

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/checkout.py backend/tests/test_checkout_guest_endpoint.py
git commit -m "feat: POST /api/checkout/guest — unauthenticated, simulated-payment checkout"
```

---

## Task 7: Frontend types + API client function

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/orders.ts`

**Interfaces:**
- Produces: `GuestAddressInput`, `CardDetailsInput`, `GuestCheckoutRequestBody`,
  `GuestCheckoutResponseBody` types; `ordersApi.guestCheckout(body) -> Promise<GuestCheckoutResponseBody>`.

- [ ] **Step 1: Edit `frontend/src/types.ts`.**

  Change `Order.user_id: number` to `Order.user_id: number | null`, and add seven
  fields right after `shipping_country` in the `Order` interface:

```typescript
  billing_name: string | null
  billing_line1: string | null
  billing_line2: string | null
  billing_city: string | null
  billing_state: string | null
  billing_postal_code: string | null
  billing_country: string | null
```

  Then append these new interfaces at the end of the file:

```typescript
export type CardBrand = 'visa' | 'mastercard' | 'discover' | 'amex'

export interface GuestAddressInput {
  name: string
  line1: string
  line2?: string | null
  city: string
  state: string
  postal_code: string
  country: string
}

export interface CardDetailsInput {
  brand: CardBrand
  number: string
  name_on_card: string
  exp_month: number
  exp_year: number
  cvv: string
  postal_code: string
}

export interface GuestCheckoutRequestBody {
  contact_email: string
  billing_address: GuestAddressInput
  card: CardDetailsInput
  same_as_billing: boolean
  shipping_address?: GuestAddressInput | null
  items: { product_id: number; quantity: number }[]
}

export interface GuestCheckoutResponseBody {
  order: Order
  email_sent: boolean
}
```

- [ ] **Step 2: Edit `frontend/src/api/orders.ts`.** Add the import and the
  method:

```typescript
import type {
  CheckoutSession,
  GuestCheckoutRequestBody,
  GuestCheckoutResponseBody,
  Order,
  Paged,
  ShippingAddressInput,
} from '../types'
```

  and, inside the `ordersApi` object, after `devConfirm`:

```typescript
  async guestCheckout(body: GuestCheckoutRequestBody): Promise<GuestCheckoutResponseBody> {
    const { data } = await api.post<GuestCheckoutResponseBody>('/checkout/guest', body)
    return data
  },
```

- [ ] **Step 3: Type-check.**

Run: `cd frontend && npm run typecheck`
Expected: no errors. (If there's an error about `Order.user_id` being used
somewhere as non-nullable, e.g. `OrderDetailPage.tsx` or `AdminOrdersPage.tsx`
doing arithmetic/comparison on it — read that file and confirm it only ever
*displays* `user_id`; if so a `number | null` is safe there and no further
change is needed. If it's used as a lookup key elsewhere, guard it with
`order.user_id != null` at that call site.)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types.ts frontend/src/api/orders.ts
git commit -m "feat: frontend types + API client for guest checkout"
```

---

## Task 8: Frontend card validation helper (mirrors backend rules)

**Files:**
- Create: `frontend/src/lib/cardValidation.ts`

**Interfaces:**
- Produces: `detectBrand(number: string): CardBrand | null`,
  `luhnIsValid(number: string): boolean`, `cvvLengthFor(brand: CardBrand): number`,
  `validateCard(input): Record<string, string>` (field name → error message, empty
  object means valid) — consumed by Task 9's form for instant feedback. This is
  UX only; Task 6's backend check is what's actually authoritative.

- [ ] **Step 1: Write the file**

```typescript
import type { CardBrand } from '../types'

const BRAND_RULES: { brand: CardBrand; prefixes: string[]; lengths: number[] }[] = [
  { brand: 'visa', prefixes: ['4'], lengths: [13, 16, 19] },
  {
    brand: 'mastercard',
    prefixes: [
      ...Array.from({ length: 5 }, (_, i) => String(51 + i)),
      ...Array.from({ length: 500 }, (_, i) => String(2221 + i)),
    ],
    lengths: [16],
  },
  {
    brand: 'discover',
    prefixes: ['6011', '65', ...Array.from({ length: 6 }, (_, i) => String(644 + i))],
    lengths: [16],
  },
  { brand: 'amex', prefixes: ['34', '37'], lengths: [15] },
]

function digitsOnly(value: string): string {
  return value.replace(/[^0-9]/g, '')
}

export function detectBrand(number: string): CardBrand | null {
  const digits = digitsOnly(number)
  for (const rule of BRAND_RULES) {
    if (!rule.lengths.includes(digits.length)) continue
    if (rule.prefixes.some((prefix) => digits.startsWith(prefix))) return rule.brand
  }
  return null
}

export function luhnIsValid(number: string): boolean {
  const digits = digitsOnly(number).split('').map(Number)
  if (digits.length === 0) return false
  let checksum = 0
  digits.reverse().forEach((digit, index) => {
    let value = digit
    if (index % 2 === 1) {
      value *= 2
      if (value > 9) value -= 9
    }
    checksum += value
  })
  return checksum % 10 === 0
}

export function cvvLengthFor(brand: CardBrand): number {
  return brand === 'amex' ? 4 : 3
}

interface CardInput {
  brand: CardBrand
  number: string
  expMonth: number
  expYear: number
  cvv: string
  postalCode: string
}

/** Field name -> error message. Empty object means the card looks valid. */
export function validateCard(input: CardInput): Record<string, string> {
  const errors: Record<string, string> = {}
  const digits = digitsOnly(input.number)

  if (digits.length < 12 || digits.length > 19) {
    errors.number = 'Card number length looks wrong.'
  } else if (!luhnIsValid(digits)) {
    errors.number = 'Card number failed the checksum check.'
  } else if (detectBrand(digits) !== input.brand) {
    errors.number = `That number doesn't look like a ${input.brand} card.`
  }

  if (input.expMonth < 1 || input.expMonth > 12) {
    errors.exp_month = 'Expiry month must be between 1 and 12.'
  } else {
    const now = new Date()
    const lastDayOfExpiryMonth = new Date(input.expYear, input.expMonth, 0)
    if (lastDayOfExpiryMonth < new Date(now.getFullYear(), now.getMonth(), now.getDate())) {
      errors.exp_year = 'This card has already expired.'
    }
  }

  const cvvDigits = digitsOnly(input.cvv)
  if (cvvDigits.length !== cvvLengthFor(input.brand)) {
    errors.cvv = `${input.brand} security codes are ${cvvLengthFor(input.brand)} digits.`
  }

  if (!/^\d{5}(-\d{4})?$/.test(input.postalCode)) {
    errors.postal_code = 'Zip code must be 5 digits (optionally +4).'
  }

  return errors
}
```

- [ ] **Step 2: Type-check.**

Run: `cd frontend && npm run typecheck`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/cardValidation.ts
git commit -m "feat: client-side card validation mirroring backend rules (UX only)"
```

---

## Task 9: Guest checkout page, cart button, route

**Files:**
- Create: `frontend/src/pages/GuestCheckoutPage.tsx`
- Modify: `frontend/src/pages/CartPage.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `ordersApi.guestCheckout` (Task 7), `validateCard`/`detectBrand`
  (Task 8), `useCartStore` (existing, for the guest's localStorage cart items and
  `clear()`), `assetUrl`/`toApiError` (existing `api/client.ts`),
  `formatMoney` (existing `lib/format.ts`).

- [ ] **Step 1: Edit `frontend/src/pages/CartPage.tsx`.** Replace the single
  checkout button block (the `<button>...Sign in to check out</button>` plus its
  wrapping) with two buttons:

```tsx
        <div className="mt-5 space-y-2">
          <button
            type="button"
            className="btn-primary w-full"
            onClick={() => navigate(user ? '/checkout' : '/login', { state: { from: '/checkout' } })}
          >
            {user ? 'Proceed to checkout' : 'Sign in to check out'}
          </button>
          {!user && (
            <button
              type="button"
              className="btn-secondary w-full"
              onClick={() => navigate('/checkout/guest')}
            >
              Checkout as guest
            </button>
          )}
        </div>
```

  (Keep the `<p className="mt-3 text-xs text-ink-700">` note below it as-is.)

- [ ] **Step 2: Add the route in `frontend/src/App.tsx`.** Import
  `GuestCheckoutPage` from `./pages/GuestCheckoutPage`, and add, next to the
  existing `checkout/cancel` line (outside `ProtectedRoute`, since guests have no
  session):

```tsx
        <Route path="checkout/guest" element={<GuestCheckoutPage />} />
```

- [ ] **Step 3: Write `frontend/src/pages/GuestCheckoutPage.tsx`.**

```tsx
import { type FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'

import { assetUrl, toApiError } from '../api/client'
import { ordersApi } from '../api/orders'
import ErrorBanner from '../components/ErrorBanner'
import { validateCard } from '../lib/cardValidation'
import { formatMoney } from '../lib/format'
import { useCartStore } from '../store/cartStore'
import type { CardBrand, GuestAddressInput, GuestCheckoutResponseBody } from '../types'

type Step = 'billing' | 'payment' | 'shipping' | 'review'

const STEPS: { key: Step; label: string }[] = [
  { key: 'billing', label: 'Contact & billing' },
  { key: 'payment', label: 'Payment' },
  { key: 'shipping', label: 'Shipping' },
  { key: 'review', label: 'Review' },
]

const EMPTY_ADDRESS: GuestAddressInput = {
  name: '', line1: '', line2: '', city: '', state: '', postal_code: '', country: 'US',
}

/** Guest checkout: no account, one request, order created already paid (simulated). */
export default function GuestCheckoutPage() {
  const cart = useCartStore((state) => state.cart)
  const clearCart = useCartStore((state) => state.clear)

  const [step, setStep] = useState<Step>('billing')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [receipt, setReceipt] = useState<GuestCheckoutResponseBody | null>(null)

  const [email, setEmail] = useState('')
  const [billing, setBilling] = useState<GuestAddressInput>(EMPTY_ADDRESS)
  const [sameAsBilling, setSameAsBilling] = useState(true)
  const [shipping, setShipping] = useState<GuestAddressInput>(EMPTY_ADDRESS)

  const [brand, setBrand] = useState<CardBrand>('visa')
  const [number, setNumber] = useState('')
  const [nameOnCard, setNameOnCard] = useState('')
  const [expMonth, setExpMonth] = useState(1)
  const [expYear, setExpYear] = useState(new Date().getFullYear())
  const [cvv, setCvv] = useState('')
  const [cardZip, setCardZip] = useState('')

  function updateBilling(field: keyof GuestAddressInput, value: string) {
    setBilling((current) => ({ ...current, [field]: value }))
  }
  function updateShipping(field: keyof GuestAddressInput, value: string) {
    setShipping((current) => ({ ...current, [field]: value }))
  }

  function validatePaymentStep(): boolean {
    const errors = validateCard({
      brand, number, expMonth, expYear, cvv, postalCode: cardZip,
    })
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const response = await ordersApi.guestCheckout({
        contact_email: email,
        billing_address: billing,
        card: {
          brand, number, name_on_card: nameOnCard, exp_month: expMonth,
          exp_year: expYear, cvv, postal_code: cardZip,
        },
        same_as_billing: sameAsBilling,
        shipping_address: sameAsBilling ? null : shipping,
        items: cart.items.map((line) => ({ product_id: line.product_id, quantity: line.quantity })),
      })
      setReceipt(response)
      await clearCart()
    } catch (caught) {
      setError(toApiError(caught).message)
    } finally {
      setSubmitting(false)
    }
  }

  if (receipt) {
    const { order, email_sent } = receipt
    return (
      <div className="mx-auto max-w-2xl py-8 text-center">
        <h1 className="font-display text-3xl text-ink-900">Order placed</h1>
        <p className="mt-2 text-ink-700">
          Order <span className="font-semibold">{order.order_number}</span> for{' '}
          {formatMoney(order.total_cents)}.
        </p>
        <p className="mt-2 text-sm text-ink-700">
          {email_sent
            ? `A receipt was emailed to ${order.contact_email}.`
            : "We couldn't email your receipt, but your order is confirmed below."}
        </p>
        <ul className="card mt-6 divide-y divide-ink-800/10 p-4 text-left">
          {order.items.map((item) => (
            <li key={item.id} className="flex items-center gap-3 py-3">
              <img src={assetUrl(item.image_url)} alt={item.product_name} className="h-12 w-12 rounded object-cover" />
              <span className="flex-1 text-sm">{item.product_name} × {item.quantity}</span>
              <span className="text-sm font-medium">{formatMoney(item.line_total_cents)}</span>
            </li>
          ))}
        </ul>
        <div className="card mt-4 p-4 text-left text-sm">
          <p className="font-semibold text-ink-900">Shipping to</p>
          <p className="mt-1 text-ink-700">
            {order.shipping_name}<br />
            {order.shipping_line1}{order.shipping_line2 ? `, ${order.shipping_line2}` : ''}<br />
            {order.shipping_city}, {order.shipping_state} {order.shipping_postal_code}
          </p>
        </div>
        <Link to="/catalog" className="btn-primary mt-6 inline-block">Keep shopping</Link>
      </div>
    )
  }

  if (cart.items.length === 0) {
    return (
      <div className="py-16 text-center">
        <h1 className="font-display text-2xl text-ink-900">Nothing to check out</h1>
        <Link to="/catalog" className="btn-primary mt-4">Browse toys</Link>
      </div>
    )
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_340px]">
      <section>
        <h1 className="font-display text-2xl text-ink-900">Checkout as guest</h1>
        <ol className="mt-4 flex flex-wrap items-center gap-2 text-sm">
          {STEPS.map((entry) => (
            <li key={entry.key} className={entry.key === step ? 'font-semibold text-ink-900' : 'text-ink-700'}>
              {entry.label}
            </li>
          ))}
        </ol>

        <ErrorBanner message={error} onDismiss={() => setError(null)} />

        <form onSubmit={submit} className="card mt-5 space-y-4 p-6">
          {step === 'billing' && (
            <>
              <div>
                <label className="label" htmlFor="guest-email">Email for the receipt</label>
                <input id="guest-email" type="email" className="input" required
                  value={email} onChange={(event) => setEmail(event.target.value)} />
              </div>
              <div>
                <label className="label" htmlFor="billing-name">Full name</label>
                <input id="billing-name" className="input" required
                  value={billing.name} onChange={(event) => updateBilling('name', event.target.value)} />
              </div>
              <div>
                <label className="label" htmlFor="billing-line1">Street line 1</label>
                <input id="billing-line1" className="input" required
                  value={billing.line1} onChange={(event) => updateBilling('line1', event.target.value)} />
              </div>
              <div>
                <label className="label" htmlFor="billing-line2">Street line 2 (optional)</label>
                <input id="billing-line2" className="input"
                  value={billing.line2 ?? ''} onChange={(event) => updateBilling('line2', event.target.value)} />
              </div>
              <div className="grid gap-4 sm:grid-cols-3">
                <input className="input" placeholder="City" required
                  value={billing.city} onChange={(event) => updateBilling('city', event.target.value)} />
                <input className="input" placeholder="State" required
                  value={billing.state} onChange={(event) => updateBilling('state', event.target.value)} />
                <input className="input" placeholder="Zip" required
                  value={billing.postal_code} onChange={(event) => updateBilling('postal_code', event.target.value)} />
              </div>
              <button type="button" className="btn-primary" disabled={!email || !billing.name || !billing.line1}
                onClick={() => setStep('payment')}>
                Continue to payment
              </button>
            </>
          )}

          {step === 'payment' && (
            <>
              <div>
                <label className="label" htmlFor="card-brand">Card type</label>
                <select id="card-brand" className="input" value={brand}
                  onChange={(event) => setBrand(event.target.value as CardBrand)}>
                  <option value="visa">Visa</option>
                  <option value="mastercard">Mastercard</option>
                  <option value="discover">Discover</option>
                  <option value="amex">American Express</option>
                </select>
              </div>
              <div>
                <label className="label" htmlFor="card-number">Card number</label>
                <input id="card-number" className="input" required value={number}
                  onChange={(event) => setNumber(event.target.value)} />
                {fieldErrors.number && <p className="mt-1 text-sm text-red-600">{fieldErrors.number}</p>}
              </div>
              <div>
                <label className="label" htmlFor="card-name">Name on card</label>
                <input id="card-name" className="input" required value={nameOnCard}
                  onChange={(event) => setNameOnCard(event.target.value)} />
              </div>
              <div className="grid gap-4 sm:grid-cols-4">
                <input className="input" type="number" placeholder="MM" min={1} max={12} required
                  value={expMonth} onChange={(event) => setExpMonth(Number(event.target.value))} />
                <input className="input" type="number" placeholder="YYYY" min={2026} max={2100} required
                  value={expYear} onChange={(event) => setExpYear(Number(event.target.value))} />
                <input className="input" placeholder="CVV" required value={cvv}
                  onChange={(event) => setCvv(event.target.value)} />
                <input className="input" placeholder="Zip" required value={cardZip}
                  onChange={(event) => setCardZip(event.target.value)} />
              </div>
              {(fieldErrors.exp_year || fieldErrors.cvv || fieldErrors.postal_code) && (
                <p className="text-sm text-red-600">
                  {fieldErrors.exp_year || fieldErrors.cvv || fieldErrors.postal_code}
                </p>
              )}
              <div className="flex gap-3">
                <button type="button" className="btn-secondary" onClick={() => setStep('billing')}>Back</button>
                <button type="button" className="btn-primary" onClick={() => validatePaymentStep() && setStep('shipping')}>
                  Continue to shipping
                </button>
              </div>
            </>
          )}

          {step === 'shipping' && (
            <>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={sameAsBilling}
                  onChange={(event) => setSameAsBilling(event.target.checked)} />
                Same as billing address
              </label>
              {!sameAsBilling && (
                <>
                  <div>
                    <label className="label" htmlFor="ship-name">Full name</label>
                    <input id="ship-name" className="input" required value={shipping.name}
                      onChange={(event) => updateShipping('name', event.target.value)} />
                  </div>
                  <div>
                    <label className="label" htmlFor="ship-line1">Street line 1</label>
                    <input id="ship-line1" className="input" required value={shipping.line1}
                      onChange={(event) => updateShipping('line1', event.target.value)} />
                  </div>
                  <div className="grid gap-4 sm:grid-cols-3">
                    <input className="input" placeholder="City" required value={shipping.city}
                      onChange={(event) => updateShipping('city', event.target.value)} />
                    <input className="input" placeholder="State" required value={shipping.state}
                      onChange={(event) => updateShipping('state', event.target.value)} />
                    <input className="input" placeholder="Zip" required value={shipping.postal_code}
                      onChange={(event) => updateShipping('postal_code', event.target.value)} />
                  </div>
                </>
              )}
              <div className="flex gap-3">
                <button type="button" className="btn-secondary" onClick={() => setStep('payment')}>Back</button>
                <button type="button" className="btn-primary"
                  disabled={!sameAsBilling && (!shipping.name || !shipping.line1)}
                  onClick={() => setStep('review')}>
                  Review order
                </button>
              </div>
            </>
          )}

          {step === 'review' && (
            <>
              <ul className="divide-y divide-ink-800/10">
                {cart.items.map((line) => (
                  <li key={line.id} className="flex items-center gap-3 py-3">
                    <img src={assetUrl(line.image_url)} alt={line.name} className="h-12 w-12 rounded object-cover" />
                    <span className="flex-1 text-sm">{line.name} × {line.quantity}</span>
                    <span className="text-sm font-medium">{formatMoney(line.line_total_cents)}</span>
                  </li>
                ))}
              </ul>
              <div className="flex gap-3">
                <button type="button" className="btn-secondary" onClick={() => setStep('shipping')}>Back</button>
                <button type="submit" className="btn-primary flex-1" disabled={submitting}>
                  {submitting ? 'Placing order…' : `Pay ${formatMoney(cart.total_cents)}`}
                </button>
              </div>
              <p className="text-xs text-ink-700">
                This is a simulated payment for demo purposes — no real card processor is contacted.
              </p>
            </>
          )}
        </form>
      </section>

      <aside className="card h-fit p-6">
        <h2 className="font-display text-xl text-ink-900">Summary</h2>
        <dl className="mt-4 space-y-2 text-sm">
          <div className="flex justify-between"><dt className="text-ink-700">Subtotal</dt><dd>{formatMoney(cart.subtotal_cents)}</dd></div>
          <div className="flex justify-between"><dt className="text-ink-700">Shipping</dt><dd>{cart.shipping_cents === 0 ? 'Free' : formatMoney(cart.shipping_cents)}</dd></div>
          <div className="flex justify-between"><dt className="text-ink-700">Tax</dt><dd>{formatMoney(cart.tax_cents)}</dd></div>
          <div className="flex justify-between border-t border-ink-800/10 pt-3 text-base font-bold"><dt>Total</dt><dd>{formatMoney(cart.total_cents)}</dd></div>
        </dl>
      </aside>
    </div>
  )
}
```

- [ ] **Step 4: Type-check.**

Run: `cd frontend && npm run typecheck`
Expected: no errors. Fix any type mismatch before moving on (this file is long —
double check `GuestAddressInput` field names match `types.ts` exactly).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/GuestCheckoutPage.tsx frontend/src/pages/CartPage.tsx frontend/src/App.tsx
git commit -m "feat: guest checkout page — billing, payment, shipping, receipt"
```

---

## Task 10: Manual browser verification

**Files:** none (verification only).

- [ ] **Step 1: Start both servers.**

Run backend: `cd backend && uvicorn app.main:app --reload`
Run frontend (separate terminal): `cd frontend && npm run dev`

- [ ] **Step 2: Walk the golden path.** In a browser at `http://localhost:5173`,
  while signed out: add a product to the cart, go to `/cart`, click "Checkout as
  guest", fill contact + billing with a real-looking address, pick Visa and enter
  `4242 4242 4242 4242` / any future expiry / `123` / a 5-digit zip, leave "same
  as billing" checked, review, submit. Confirm: the receipt screen shows the item
  image, name, quantity, shipping address, and total; no console errors in the
  browser dev tools; the backend terminal shows the order was created (check
  `GET http://localhost:8000/api/orders/<order_number>` via `/docs` if useful,
  though that endpoint requires auth so this is just for eyeballing the DB via
  the admin UI if signed in as admin separately).

- [ ] **Step 3: Walk the edge cases.** Repeat with: "same as billing" unchecked
  (confirm a different shipping address gets used and shows correctly on the
  receipt); a card number that fails Luhn (confirm an inline error, no request
  sent that succeeds); a brand/number mismatch (pick Mastercard, type a `4242…`
  Visa number — confirm rejection); an expired date (confirm rejection); enough
  quantity to exceed stock (confirm the 409 surfaces as a readable error, not a
  raw stack trace).

- [ ] **Step 4: Confirm the existing signed-in flow still works unchanged.** Sign
  in, add to cart, "Proceed to checkout", complete the existing Stripe-hosted
  (dev-mode) flow exactly as before — this proves Task 6 didn't regress it.

- [ ] **Step 5: Report back.** Summarize what was checked and any issue found —
  this step doesn't get a commit; it's the final sign-off before calling the
  feature done.

---

## Self-review notes (already applied above)

- Every task ends with a runnable verification command and an explicit expected
  result — no "add appropriate error handling"-style placeholders.
- Field/type names are consistent across tasks: `card_brand`/`card_last4`/
  `card_exp_month`/`card_exp_year` (Payment), `billing_*`/`GuestAddress` fields
  (`name`, `line1`, `line2`, `city`, `state`, `postal_code`, `country`) match
  from the schema (Task 4) through the service (Task 5) to the frontend types
  (Task 7) and the form (Task 9).
- Every spec decision has a task: nullable `user_id` + billing columns → Task 1;
  Stripe flow untouched → verified explicitly in Task 6 Step 5 and Task 10 Step
  4; simulated-only payment → Task 5 (no Stripe import anywhere in
  `create_guest_order`); brand-mismatch rejection → Task 2 + Task 8; receipt
  returned inline, no lookup endpoint → Task 6's response shape; real Gmail SMTP
  → Task 3; email failure doesn't block the order → Task 6 Step 3 try/except.
