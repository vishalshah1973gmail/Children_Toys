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
