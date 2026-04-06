from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.logging.config import get_logger

log = get_logger(__name__)


def send_new_application_notification(
    application_public_id: str,
    *,
    _db: Session | None = None,
) -> None:
    """
    Send a notification email to the admin when a new application is submitted.

    Designed to run as a FastAPI BackgroundTask — opens its own DB session so
    it runs after the request session has already committed and closed.

    The ``_db`` parameter is a test seam: pass the test session to avoid
    opening a second connection to the real database.

    Silently exits (with a log warning) if notifications are disabled or SMTP
    settings are incomplete.
    """
    settings = get_settings()

    if not settings.NOTIFICATIONS_ENABLED:
        return

    missing = [
        name
        for name, val in [
            ("SMTP_HOST", settings.SMTP_HOST),
            ("SMTP_USER", settings.SMTP_USER),
            ("SMTP_PASSWORD", settings.SMTP_PASSWORD),
            ("SMTP_NOTIFICATION_TO", settings.SMTP_NOTIFICATION_TO),
        ]
        if not val
    ]
    if missing:
        log.warning(
            "email.notification_skipped",
            reason="incomplete_config",
            missing_fields=missing,
            application_id=application_public_id,
        )
        return

    own_session = _db is None
    db: Session = _db if _db is not None else SessionLocal()
    try:
        from app.models.application import Application  # noqa: PLC0415

        application = (
            db.query(Application)
            .filter(Application.public_id == application_public_id)
            .first()
        )
        if application is None:
            log.warning(
                "email.notification_skipped",
                reason="application_not_found",
                application_id=application_public_id,
            )
            return

        _send_smtp(
            smtp_host=settings.SMTP_HOST,  # type: ignore[arg-type]
            smtp_port=settings.SMTP_PORT,
            smtp_user=settings.SMTP_USER,  # type: ignore[arg-type]
            smtp_password=settings.SMTP_PASSWORD,  # type: ignore[arg-type]
            to=settings.SMTP_NOTIFICATION_TO,  # type: ignore[arg-type]
            subject=f"New Application: {application.job.title}",
            body=(
                f"A new application has been submitted.\n\n"
                f"Applicant: {application.applicant_name}\n"
                f"Email:     {application.applicant_email}\n"
                f"Job:       {application.job.title}\n"
                f"ID:        {application.public_id}\n"
            ),
        )
        log.info(
            "email.notification_sent",
            application_id=application_public_id,
            to=settings.SMTP_NOTIFICATION_TO,
        )

    except Exception as exc:
        log.error(
            "email.notification_failed",
            application_id=application_public_id,
            error=str(exc),
        )
    finally:
        if own_session:
            db.close()


def _send_smtp(
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    to: str,
    subject: str,
    body: str,
) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(smtp_host, smtp_port) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(smtp_user, smtp_password)
        smtp.sendmail(smtp_user, to, msg.as_string())
