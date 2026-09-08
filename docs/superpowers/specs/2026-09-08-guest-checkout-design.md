# Guest Checkout — Design Spec

Date: 2026-09-08
Status: Approved, implementing

## Problem

Cart currently forces sign-in before checkout (`CheckoutPage.tsx`, `/api/checkout/session`
require an authenticated user). Need a second path: guest checkout with its own
address/card form, simulated payment, DB persistence, and an emailed receipt. The
existing signed-in Stripe-hosted-redirect flow is untouched and stays exactly as is.

## Decisions (from clarifying-question round)

1. Guest orders: `Order.user_id` becomes nullable; guest name/email live directly on
   the order row (`contact_email`, `billing_name`, `shipping_name`). No shadow `User`
   row is created for guests.
2. Old Stripe-hosted flow and new guest flow coexist. Signed-in users keep using
   `/api/checkout/session` unchanged. Guests use a new `/api/checkout/guest` endpoint.
3. Guest payment is fully simulated — no Stripe call. Our own validation is the only
   gate; on success the order is created already `PAID`.
4. Card data: CVV is never persisted, full card number is never persisted. Only
   `card_brand`, `card_last4`, `card_exp_month`, `card_exp_year` are stored, on the
   `Payment` row.
5. Card number must match the selected brand's prefix/length rules — mismatch is a
   validation error, not silently accepted.
6. Receipt is returned in full in the `/api/checkout/guest` response body (items,
   image, qty, shipping address, totals). No separate public order-lookup endpoint —
   out of scope, YAGNI.
7. Receipt email sent via real Gmail SMTP (app password in `.env`, user-supplied).
   If the send fails, the order still stands (guest was already "charged" in the
   simulation) but the response carries `email_sent: false` and the exact SMTP error
   is logged — never swallowed silently.

## A. Schema changes

New Alembic migration, one revision:

- `orders.user_id`: `NOT NULL` → nullable.
- `orders` gains, mirroring the existing `shipping_*` columns:
  `billing_name VARCHAR(120) NULL`, `billing_line1 VARCHAR(200) NULL`,
  `billing_line2 VARCHAR(200) NULL`, `billing_city VARCHAR(120) NULL`,
  `billing_state VARCHAR(120) NULL`, `billing_postal_code VARCHAR(20) NULL`,
  `billing_country VARCHAR(2) NULL`.
  Nullable because existing Stripe-flow orders never collect a billing address.
- `payments` gains: `card_brand VARCHAR(20) NULL`, `card_last4 VARCHAR(4) NULL`,
  `card_exp_month SMALLINT NULL`, `card_exp_year SMALLINT NULL`.

`Order.user` relationship becomes `Mapped["User | None"]`.

## B. Card validation service

New file: `backend/app/services/card_validation.py`. Pure functions, no I/O, no DB:

- `detect_brand(number: str) -> str | None` — prefix/length rules:
  - Visa: starts with `4`, length 13/16/19.
  - Mastercard: `51`–`55` or `2221`–`2720`, length 16.
  - Discover: `6011`, `644`–`649`, `65`, length 16.
  - American Express: `34` or `37`, length 15.
- `luhn_is_valid(number: str) -> bool` — standard mod-10 checksum.
- `cvv_length_for(brand: str) -> int` — 4 for Amex, 3 otherwise.
- `validate_card(brand, number, exp_month, exp_year, cvv, today) -> list[FieldError]`
  — runs all checks, returns every failure (not just the first), so the form can
  show them all at once:
  - number strips spaces/dashes, digits only, length 12–19.
  - Luhn check.
  - detected brand must equal the brand the user selected (decision 5).
  - `exp_month` in 1–12.
  - expiry (last day of `exp_month/exp_year`) must not be in the past relative to `today`.
  - `cvv` digits only, length must equal `cvv_length_for(brand)`.

Unit tests cover: valid Visa/MC/Discover/Amex, failed Luhn, brand/number mismatch,
expired card, wrong CVV length per brand, non-digit input.

## C. `POST /api/checkout/guest`

No auth dependency. New Pydantic schemas in `app/schemas/checkout_guest.py`:

```
GuestAddress: name, line1, line2?, city, state, postal_code, country="US"
CardDetails: brand (enum: visa|mastercard|discover|amex), number, name_on_card,
             exp_month, exp_year, cvv, postal_code
GuestCheckoutItem: product_id, quantity
GuestCheckoutRequest:
    contact_email: EmailStr
    billing_address: GuestAddress
    card: CardDetails
    same_as_billing: bool
    shipping_address: GuestAddress | None   # required when same_as_billing is False
    items: list[GuestCheckoutItem]          # min length 1
GuestCheckoutResponse:
    order: OrderRead
    email_sent: bool
```

New `order_service.create_guest_order(db, payload) -> Order`:

1. Reject empty `items` → `400 empty_cart` (matches existing convention).
2. Load each `product_id`, recompute price/stock server-side — same
   `insufficient_stock` / `product_unavailable` checks as `create_pending_order`,
   never trusting client-sent prices.
3. Run `card_validation.validate_card(...)`. Any failure → `422 invalid_card` with
   the field name(s) (reuses the existing `ErrorDetail` shape via `api_error`).
4. Compute totals via existing `pricing.totals_for`.
5. Build `Order(user_id=None, status=PAID, placed_at=now, paid_at=now, ...)` with
   `contact_email`, `billing_*` from `billing_address`, `shipping_*` from
   `shipping_address` if `same_as_billing` is False else copied from
   `billing_address`.
6. Append `OrderItem` rows (same snapshot pattern as today).
7. Decrement stock immediately (guest orders skip the pending→paid step entirely —
   there is no webhook to wait for).
8. Add a `Payment(provider="guest_form", status=SUCCEEDED, amount_cents=total,
   card_brand=..., card_last4=number[-4:], card_exp_month=..., card_exp_year=...)`.
   The full card number and CVV are never passed into this call.
9. Commit, refresh.

Router (`app/routers/checkout.py`, new handler) then calls
`email_service.send_receipt(order)`, catches any exception, logs it, and sets
`email_sent` accordingly — never lets an email failure roll back or fail the request.

## D. Email

New settings in `app/core/config.py`: `smtp_host`, `smtp_port` (default 587),
`smtp_user`, `smtp_app_password`, `email_from`. Added (blank defaults) to
`.env.example` — real values go in `.env`, which is already gitignored.

New `app/services/email_service.py`: `send_receipt(order: Order) -> None`, builds a
small HTML email (item image/name/qty, shipping address, totals) and sends it via
`smtplib.SMTP(host, port)` + `starttls()` + login, to `order.contact_email`. Raises
on failure — the router is the one place that decides to swallow-and-log.

## E. Frontend

- `CartPage.tsx`: add a "Checkout as Guest" button next to "Sign in to checkout".
- New `GuestCheckoutPage.tsx`, steps in one page (not separate routes, to keep the
  guest's in-memory cart simple):
  1. Contact email + billing address (name + full address).
  2. Payment method: brand select (Visa/Mastercard/Discover/Amex) + card number,
     name on card, expiry, CVV, zip. Client-side mirrors the backend's validation
     rules for instant feedback; backend stays authoritative.
  3. Shipping: "Same as billing address" checkbox; unchecked reveals name + address
     fields.
  4. Review + submit → calls `POST /api/checkout/guest` with the current
     `localStorage` guest cart lines as `items`.
- On success: render the receipt inline from the response (item image, description,
  qty, shipping address, total, "receipt emailed to {contact_email}" or a fallback
  notice when `email_sent` is false), then clear the guest `localStorage` cart.
- On `422 invalid_card` / `409 insufficient_stock` etc: surface the field-level error
  next to the relevant input, same pattern the rest of the app already uses for
  API errors.

## F. Tests

Backend:
- `tests/test_card_validation.py` — unit tests per brand, Luhn failures, mismatch,
  expiry, CVV length.
- `tests/test_checkout_guest.py` — integration: happy path (order created PAID, stock
  decremented, `Payment` row has brand/last4 only, no PAN/CVV anywhere), empty cart,
  insufficient stock, invalid card (each failure mode), email failure still returns
  201 with `email_sent: false`.

Frontend: manual walkthrough in browser (dev server) once built — guest add-to-cart →
checkout → submit → receipt shown → confirm no console errors.

## Out of scope (explicitly)

- Any real Stripe call for the guest path.
- Public/guest order-lookup endpoint (viewing a past guest receipt again).
- Linking a guest order to an existing account by matching email.
- Changing the signed-in Stripe-hosted flow in any way.
