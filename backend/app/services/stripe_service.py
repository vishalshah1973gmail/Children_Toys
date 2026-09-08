"""Thin wrapper around the Stripe SDK.

When STRIPE_SECRET_KEY is blank the backend runs in "dev payment" mode: no
Stripe call is made and the frontend is redirected to a local confirmation
page instead. That keeps the app runnable before any Stripe keys exist.
"""

from __future__ import annotations

from typing import Any

import stripe
from fastapi import status

from app.core.config import settings
from app.core.errors import api_error
from app.models.order import Order


def _configure() -> None:
    stripe.api_key = settings.stripe_secret_key


def create_checkout_session(order: Order) -> Any:
    """Create a Stripe Checkout Session priced entirely from the order rows."""
    _configure()

    line_items = [
        {
            "price_data": {
                "currency": order.currency,
                "unit_amount": item.unit_price_cents,
                "product_data": {"name": item.product_name},
            },
            "quantity": item.quantity,
        }
        for item in order.items
    ]

    if order.shipping_cents > 0:
        line_items.append(
            {
                "price_data": {
                    "currency": order.currency,
                    "unit_amount": order.shipping_cents,
                    "product_data": {"name": "Shipping"},
                },
                "quantity": 1,
            }
        )
    if order.tax_cents > 0:
        line_items.append(
            {
                "price_data": {
                    "currency": order.currency,
                    "unit_amount": order.tax_cents,
                    "product_data": {"name": "Sales tax"},
                },
                "quantity": 1,
            }
        )

    try:
        return stripe.checkout.Session.create(
            mode="payment",
            line_items=line_items,
            customer_email=order.contact_email,
            client_reference_id=order.order_number,
            metadata={"order_number": order.order_number, "order_id": str(order.id)},
            success_url=(
                f"{settings.checkout_success_url}"
                f"?order_number={order.order_number}&session_id={{CHECKOUT_SESSION_ID}}"
            ),
            cancel_url=f"{settings.checkout_cancel_url}?order_number={order.order_number}",
        )
    except stripe.error.StripeError as exc:  # pragma: no cover - network path
        raise api_error(
            status.HTTP_502_BAD_GATEWAY,
            "stripe_error",
            f"Stripe rejected the checkout session: {exc.user_message or str(exc)}",
        )


def construct_event(payload: bytes, signature_header: str | None) -> Any:
    """Verify the Stripe signature and return the parsed event."""
    if not settings.stripe_webhook_secret:
        raise api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "webhook_not_configured",
            "STRIPE_WEBHOOK_SECRET is not set",
        )
    if not signature_header:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "missing_signature",
            "Stripe-Signature header is missing",
        )

    _configure()
    try:
        return stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature_header,
            secret=settings.stripe_webhook_secret,
        )
    except ValueError:
        raise api_error(
            status.HTTP_400_BAD_REQUEST, "invalid_payload", "Webhook payload is not valid JSON"
        )
    except stripe.error.SignatureVerificationError:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_signature",
            "Webhook signature verification failed",
        )
