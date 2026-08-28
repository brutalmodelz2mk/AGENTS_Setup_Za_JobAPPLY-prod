"""Email service (spec §10).

Sends only after human approval (enforced by the calling node). Never stores a
provider password in source; credentials come from Settings. This implementation
uses SMTP (Gmail app password). Swap the backend to Gmail API / SendGrid by
implementing the same interface.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger("dzvonko.email")


class EmailNotConfigured(RuntimeError):
    """Raised when an email send is attempted without credentials."""


@dataclass
class EmailMessage:
    recipient: str
    subject: str
    body: str
    application_id: str | None = None


class EmailService:
    def __init__(self, provider: str | None = None) -> None:
        self.provider = (provider or settings.email_provider).lower()

    @property
    def configured(self) -> bool:
        return bool(settings.email_smtp_user and settings.email_smtp_password)

    def send(self, msg: EmailMessage) -> dict[str, str]:
        """Send a message after approval. Raises EmailNotConfigured if unset."""
        if not self.configured:
            raise EmailNotConfigured(
                "Email provider is not configured. Set EMAIL_SMTP_USER / "
                "EMAIL_SMTP_PASSWORD in .env."
            )
        if self.provider in ("smtp", "gmail"):
            return self._send_smtp(msg)
        raise NotImplementedError(f"Email provider {self.provider!r} not implemented")

    def _send_smtp(self, msg: EmailMessage) -> dict[str, str]:
        import smtplib
        from email.message import EmailMessage as Em

        em = Em()
        em["Subject"] = msg.subject
        em["From"] = settings.email_smtp_user
        em["To"] = msg.recipient
        em.set_content(msg.body)

        with smtplib.SMTP(settings.email_smtp_host, settings.email_smtp_port, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(settings.email_smtp_user, settings.email_smtp_password)
            smtp.send_message(em)
        logger.info("Email sent to %s (%s)", msg.recipient, self.provider)
        return {"status": "sent", "recipient": msg.recipient, "provider": self.provider}


default_email_service = EmailService()
