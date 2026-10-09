"""Best-effort emails for the registration approval flow.

Each function returns whether the email went out. They never raise: an email
problem must not undo a registration or an admin decision.
"""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User, UserRole
from app.services import email_service

logger = logging.getLogger(__name__)


def _admin_recipient(db: Session) -> str | None:
    if settings.admin_notify_email:
        return settings.admin_notify_email
    return db.execute(
        select(User.email).where(User.role == UserRole.ADMIN).order_by(User.id).limit(1)
    ).scalar_one_or_none()


def _send(to: str, subject_and_html: tuple[str, str], what: str) -> bool:
    subject, html = subject_and_html
    try:
        email_service.send_mail(to, subject, html)
        return True
    except Exception:
        logger.warning("Could not send %s email to %s", what, to, exc_info=True)
        return False


def notify_admin_new_registration(db: Session, user: User) -> bool:
    try:
        recipient = _admin_recipient(db)
        if recipient is None:
            logger.warning("No admin email available for new registration %s", user.username)
            return False
        return _send(
            recipient, email_service.render_admin_notice(user), "admin registration notice"
        )
    except Exception:
        logger.warning("Could not prepare admin registration notice", exc_info=True)
        return False


def notify_approved(user: User) -> bool:
    try:
        return _send(user.email, email_service.render_approved(user), "approval")
    except Exception:
        logger.warning("Could not prepare approval email", exc_info=True)
        return False


def notify_rejected(user: User) -> bool:
    try:
        return _send(user.email, email_service.render_rejected(user), "rejection")
    except Exception:
        logger.warning("Could not prepare rejection email", exc_info=True)
        return False
