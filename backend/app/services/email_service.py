"""Guest-checkout receipt and registration emails, sent over real SMTP (Gmail + app password).

Raises on any failure. The caller decides whether that should block the
checkout response — see routers/checkout.py, which logs and continues.
Registration emails are sent best-effort via services/registration_service.py.
"""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

from app.core.config import settings
from app.models.order import Order
from app.models.user import User


def _absolute_image_url(image_url: str | None) -> str:
    if not image_url:
        return ""
    if image_url.startswith("http"):
        return image_url
    return f"{settings.public_base_url}{image_url if image_url.startswith('/') else '/' + image_url}"


def _render_html(order: Order) -> str:
    rows = "".join(
        f"<tr><td><img src='{_absolute_image_url(item.image_url)}' width='48' /></td>"
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


class EmailNotConfigured(RuntimeError):
    """SMTP settings are empty, so nothing can be sent."""


def send_mail(to: str, subject: str, html: str) -> None:
    """Send one HTML email. Raises EmailNotConfigured or an smtplib/OSError on failure."""
    if not settings.smtp_host:
        raise EmailNotConfigured("SMTP_HOST is not set")
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = settings.email_from or settings.smtp_user
    message["To"] = to
    message.attach(MIMEText(html, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_app_password)
        server.sendmail(message["From"], [to], message.as_string())


def _display_name(user: User) -> str:
    return escape(user.full_name or user.username)


def render_admin_notice(user: User) -> tuple[str, str]:
    """Tell the admin someone is waiting for approval."""
    portal = f"{settings.frontend_base_url}/admin/approvals"
    html = (
        "<h2>New registration awaiting approval</h2>"
        f"<p><strong>Name:</strong> {escape(user.full_name or '-')}<br>"
        f"<strong>Username:</strong> {escape(user.username)}<br>"
        f"<strong>Email:</strong> {escape(user.email)}</p>"
        f"<p>Log in to the Admin Portal and approve or reject this request: "
        f"<a href='{portal}'>{portal}</a></p>"
    )
    return f"New registration request: {user.username}", html


def render_approved(user: User) -> tuple[str, str]:
    """Welcome email with the login link."""
    login_url = f"{settings.frontend_base_url}/login"
    html = (
        f"<h2>Welcome to ToyBox, {_display_name(user)}!</h2>"
        "<p>Your registration has been approved. You can now sign in with the "
        "username and password you chose.</p>"
        f"<p><a href='{login_url}'>{login_url}</a></p>"
    )
    return "Your ToyBox registration is approved", html


def render_rejected(user: User) -> tuple[str, str]:
    """Rejection email carrying the admin's reason."""
    html = (
        f"<h2>Hello {_display_name(user)},</h2>"
        "<p>Your ToyBox registration was not approved.</p>"
        f"<p><strong>Reason:</strong> {escape(user.rejection_reason or '')}</p>"
        "<p>You will not be able to sign in with this account.</p>"
    )
    return "Your ToyBox registration was not approved", html
