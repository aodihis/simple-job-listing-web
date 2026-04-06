from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import SessionLocal
from app.logging.config import get_logger

log = get_logger(__name__)

# Fields required for any outbound email (admin notification or applicant auto-reply).
_REQUIRED_SMTP_FIELDS = ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"]


def _check_enabled(settings: Settings, context: str) -> bool:
    """Return True if notifications are enabled and core SMTP config is present."""
    if not settings.NOTIFICATIONS_ENABLED:
        return False

    missing = [name for name in _REQUIRED_SMTP_FIELDS if not getattr(settings, name)]
    if missing:
        log.warning(
            "email.notification_skipped",
            reason="incomplete_config",
            missing_fields=missing,
            context=context,
        )
        return False

    return True


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

    if not _check_enabled(settings, "admin_notification"):
        return

    if not settings.SMTP_NOTIFICATION_TO:
        log.warning(
            "email.notification_skipped",
            reason="incomplete_config",
            missing_fields=["SMTP_NOTIFICATION_TO"],
            context="admin_notification",
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
            from_name=settings.SMTP_FROM_NAME,
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


def send_application_confirmation(
    application_public_id: str,
    *,
    _db: Session | None = None,
) -> None:
    """
    Send a confirmation email to the applicant after they submit an application.

    Designed to run as a FastAPI BackgroundTask — opens its own DB session so
    it runs after the request session has already committed and closed.

    The ``_db`` parameter is a test seam: pass the test session to avoid
    opening a second connection to the real database.

    Silently exits (with a log warning) if notifications are disabled or SMTP
    settings are incomplete.
    """
    settings = get_settings()

    if not _check_enabled(settings, "applicant_confirmation"):
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
                "email.confirmation_skipped",
                reason="application_not_found",
                application_id=application_public_id,
            )
            return

        job_title = application.job.title
        applicant_name = application.applicant_name
        applicant_email = application.applicant_email

        _send_smtp(
            smtp_host=settings.SMTP_HOST,  # type: ignore[arg-type]
            smtp_port=settings.SMTP_PORT,
            smtp_user=settings.SMTP_USER,  # type: ignore[arg-type]
            smtp_password=settings.SMTP_PASSWORD,  # type: ignore[arg-type]
            from_name=settings.SMTP_FROM_NAME,
            to=applicant_email,
            subject=f"We received your application — {job_title}",
            body=(
                f"Hi {applicant_name},\n\n"
                f"Thank you for applying for the {job_title} position. "
                f"We have received your application and will be in touch if your profile is a good fit.\n\n"
                f"Best regards"
            ),
        )
        log.info(
            "email.confirmation_sent",
            application_id=application_public_id,
            to=applicant_email,
        )

    except Exception as exc:
        log.error(
            "email.confirmation_failed",
            application_id=application_public_id,
            error=str(exc),
        )
    finally:
        if own_session:
            db.close()


def send_test_email(to: str) -> None:
    """
    Send a test email to verify SMTP configuration.

    Raises an exception (SMTP errors, connection errors, config errors) so the
    caller can surface a meaningful error message to the admin.
    """
    settings = get_settings()

    missing = [name for name in _REQUIRED_SMTP_FIELDS if not getattr(settings, name)]
    if missing:
        raise ValueError(f"Incomplete SMTP configuration — missing: {', '.join(missing)}")

    _send_smtp(
        smtp_host=settings.SMTP_HOST,  # type: ignore[arg-type]
        smtp_port=settings.SMTP_PORT,
        smtp_user=settings.SMTP_USER,  # type: ignore[arg-type]
        smtp_password=settings.SMTP_PASSWORD,  # type: ignore[arg-type]
        from_name=settings.SMTP_FROM_NAME,
        to=to,
        subject="Test email — SMTP configuration check",
        body=(
            "This is a test email sent from the admin dashboard.\n\n"
            "If you received this, your SMTP configuration is working correctly."
        ),
    )
    log.info("email.test_sent", to=to)


def _send_smtp(
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    from_name: str | None,
    to: str,
    subject: str,
    body: str,
) -> None:
    from_addr = f"{from_name} <{smtp_user}>" if from_name else smtp_user

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(smtp_host, smtp_port) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(smtp_user, smtp_password)
        smtp.sendmail(smtp_user, to, msg.as_string())
