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
