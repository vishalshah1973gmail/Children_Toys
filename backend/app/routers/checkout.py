"""Stripe Checkout session creation and the payment webhook."""

import logging

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.errors import api_error, not_found
from app.db.session import get_db
from app.models.order import OrderStatus
from app.models.user import User
from app.schemas.checkout_guest import GuestCheckoutRequest, GuestCheckoutResponse
from app.schemas.common import Message
from app.schemas.order import CheckoutRequest, CheckoutSessionResponse, OrderRead
from app.services import email_service, order_service, stripe_service

router = APIRouter(tags=["checkout"])
logger = logging.getLogger(__name__)


@router.post(
    "/checkout/session",
    response_model=CheckoutSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_checkout_session(
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CheckoutSessionResponse:
    """Create a pending order from the server-side cart and hand back a pay URL.

    Stock is validated here but not decremented: that happens only once the
    webhook confirms the payment succeeded.
    """
    order = order_service.create_pending_order(db, current_user, payload)

    if not settings.stripe_enabled:
        if not settings.allow_dev_payment:
            db.rollback()
            raise api_error(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "payments_unavailable",
                "Stripe is not configured on this server",
            )
        db.commit()
        return CheckoutSessionResponse(
            order_number=order.order_number,
            checkout_url=(
                f"{settings.checkout_success_url}"
                f"?order_number={order.order_number}&dev=1"
            ),
            dev_mode=True,
        )

    session = stripe_service.create_checkout_session(order)
    order.stripe_session_id = session.id
    db.commit()

    return CheckoutSessionResponse(
        order_number=order.order_number,
        checkout_url=session.url,
        session_id=session.id,
    )


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


@router.post("/checkout/dev-confirm/{order_number}", response_model=OrderRead)
def dev_confirm(
    order_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderRead:
    """Local-only stand-in for the Stripe webhook.

    Available only while Stripe is unconfigured and ALLOW_DEV_PAYMENT is true,
    so the storefront can be exercised end to end without Stripe keys.
    """
    if settings.stripe_enabled or not settings.allow_dev_payment:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "not_found",
            "Dev payment confirmation is disabled",
        )

    order = order_service.get_order_by_number(db, order_number)
    if order is None or order.user_id != current_user.id:
        raise not_found("Order")

    order_service.mark_order_paid(db, order, provider="dev")
    db.commit()
    db.refresh(order)
    return OrderRead.model_validate(order)


@router.post("/webhooks/stripe", response_model=Message)
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> Message:
    """Verify the Stripe signature and confirm or fail the matching order."""
    payload = await request.body()
    event = stripe_service.construct_event(payload, stripe_signature)

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        if data.get("payment_status") != "paid":
            return Message(message="Session completed but not paid; ignored")

        order = None
        reference = data.get("client_reference_id")
        if reference:
            order = order_service.get_order_by_number(db, reference)
        if order is None and data.get("id"):
            order = order_service.get_order_by_session(db, data["id"])
        if order is None:
            return Message(message="No matching order; ignored")

        if order.status != OrderStatus.PENDING:
            return Message(message="Order already processed")

        payment_intent = data.get("payment_intent")
        order_service.mark_order_paid(
            db,
            order,
            payment_intent_id=payment_intent if isinstance(payment_intent, str) else None,
            session_id=data.get("id"),
            event_id=event.get("id"),
        )
        db.commit()
        return Message(message=f"Order {order.order_number} marked paid")

    if event_type in {"checkout.session.expired", "payment_intent.payment_failed"}:
        session_id = data.get("id") if event_type.startswith("checkout") else None
        order = order_service.get_order_by_session(db, session_id) if session_id else None
        if order is not None and order.status == OrderStatus.PENDING:
            order_service.record_failed_payment(
                db, order, reason=event_type, event_id=event.get("id")
            )
            db.commit()
        return Message(message="Failure recorded")

    return Message(message=f"Ignored event {event_type}")
