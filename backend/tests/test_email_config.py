"""
Tests for email_service.send_new_application_notification.

SMTP settings come from environment variables (via get_settings), not from the
database, so tests mock get_settings() rather than seeding a DB row.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ADMIN_JOBS_URL = "/api/v1/admin/jobs"
PUBLIC_APPLY_URL = "/api/v1/jobs/{job_id}/apply"

ADMIN = {
    "email": "admin@example.com",
    "display_name": "Test Admin",
    "password": "securepassword123",
}

BASE_JOB = {
    "title": "Engineer",
    "description": "<p>Great role.</p>",
    "employment_type": "full_time",
    "location": "Remote",
    "is_remote": True,
    "application_mode": "form",
    "external_apply_url": None,
    "tags": [],
    "expires_at": None,
}

FULL_SMTP_SETTINGS = {
    "NOTIFICATIONS_ENABLED": True,
    "SMTP_HOST": "smtp.example.com",
    "SMTP_PORT": 587,
    "SMTP_USER": "user@example.com",
    "SMTP_PASSWORD": "secret",
    "SMTP_FROM_NAME": None,
    "SMTP_NOTIFICATION_TO": "admin@example.com",
}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def auth_headers(client: TestClient) -> dict:
    client.post(REGISTER_URL, json=ADMIN)
    resp = client.post(LOGIN_URL, json={"email": ADMIN["email"], "password": ADMIN["password"]})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _make_settings(**overrides):
    """Return a mock Settings object with full SMTP config, with optional overrides."""
    from app.config import Settings
    defaults = FULL_SMTP_SETTINGS.copy()
    defaults.update(overrides)
    s = MagicMock(spec=Settings)
    for k, v in defaults.items():
        setattr(s, k, v)
    return s


def _seed_application(db: Session) -> str:
    """Insert a job + application, return the application public_id."""
    from app.models.application import Application
    from app.models.job import Job
    from app.models.user import AdminUser
    from app.utils.security import hash_password

    user = AdminUser(
        email="a@b.com",
        display_name="A",
        password_hash=hash_password("pw"),
        is_active=True,
    )
    db.add(user)
    db.flush()

    job = Job(
        title="Dev",
        description="desc",
        employment_type="full_time",
        is_remote=False,
        application_mode="form",
        is_active=True,
        is_deleted=False,
        posted_by=user,
    )
    db.add(job)
    db.flush()

    application = Application(
        job_id=job.id,
        applicant_name="Alice",
        applicant_email="alice@example.com",
    )
    application.responses = {}
    db.add(application)
    db.flush()

    return application.public_id


# ── send_new_application_notification ─────────────────────────────────────────

class TestSendNewApplicationNotification:
    def test_sends_email_when_enabled(self, db_session: Session) -> None:
        from app.services.email_service import send_new_application_notification

        app_id = _seed_application(db_session)

        with patch("app.services.email_service.get_settings", return_value=_make_settings()):
            with patch("smtplib.SMTP") as mock_smtp_cls:
                mock_smtp = MagicMock()
                mock_smtp_cls.return_value.__enter__ = lambda s: mock_smtp
                mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
                send_new_application_notification(app_id, _db=db_session)

        mock_smtp.sendmail.assert_called_once()
        args = mock_smtp.sendmail.call_args[0]
        assert args[0] == "user@example.com"
        assert args[1] == "admin@example.com"

    def test_skips_when_notifications_disabled(self, db_session: Session) -> None:
        from app.services.email_service import send_new_application_notification

        app_id = _seed_application(db_session)

        with patch(
            "app.services.email_service.get_settings",
            return_value=_make_settings(NOTIFICATIONS_ENABLED=False),
        ):
            with patch("smtplib.SMTP") as mock_smtp_cls:
                send_new_application_notification(app_id, _db=db_session)
                mock_smtp_cls.assert_not_called()

    def test_skips_when_smtp_host_missing(self, db_session: Session) -> None:
        from app.services.email_service import send_new_application_notification

        app_id = _seed_application(db_session)

        with patch(
            "app.services.email_service.get_settings",
            return_value=_make_settings(SMTP_HOST=None),
        ):
            with patch("smtplib.SMTP") as mock_smtp_cls:
                send_new_application_notification(app_id, _db=db_session)
                mock_smtp_cls.assert_not_called()

    def test_skips_when_application_not_found(self, db_session: Session) -> None:
        from app.services.email_service import send_new_application_notification

        with patch("app.services.email_service.get_settings", return_value=_make_settings()):
            with patch("smtplib.SMTP") as mock_smtp_cls:
                send_new_application_notification("nonexistent-id", _db=db_session)
                mock_smtp_cls.assert_not_called()

    def test_does_not_raise_on_smtp_failure(self, db_session: Session) -> None:
        from app.services.email_service import send_new_application_notification

        app_id = _seed_application(db_session)

        with patch("app.services.email_service.get_settings", return_value=_make_settings()):
            with patch("smtplib.SMTP", side_effect=ConnectionRefusedError("refused")):
                # Must not raise — background tasks must be resilient
                send_new_application_notification(app_id, _db=db_session)

    def test_background_task_triggered_on_apply(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """Integration: POST /jobs/{id}/apply enqueues the background task."""
        from io import BytesIO

        job_resp = client.post(ADMIN_JOBS_URL, json=BASE_JOB, headers=auth_headers)
        job_id = job_resp.json()["public_id"]

        with patch(
            "app.services.email_service.send_new_application_notification"
        ) as mock_notify:
            resp = client.post(
                PUBLIC_APPLY_URL.format(job_id=job_id),
                data={"applicant_name": "Alice", "applicant_email": "alice@x.com", "responses_json": "{}"},
                files={"cv_file": ("cv.pdf", BytesIO(b"%PDF fake"), "application/pdf")},
            )
            assert resp.status_code == 201
            # TestClient runs background tasks synchronously
            mock_notify.assert_called_once()


# ── send_application_confirmation ─────────────────────────────────────────────

class TestSendApplicationConfirmation:
    def test_sends_email_to_applicant(self, db_session: Session) -> None:
        from app.services.email_service import send_application_confirmation

        app_id = _seed_application(db_session)

        with patch("app.services.email_service.get_settings", return_value=_make_settings()):
            with patch("smtplib.SMTP") as mock_smtp_cls:
                mock_smtp = MagicMock()
                mock_smtp_cls.return_value.__enter__ = lambda s: mock_smtp
                mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
                send_application_confirmation(app_id, _db=db_session)

        mock_smtp.sendmail.assert_called_once()
        args = mock_smtp.sendmail.call_args[0]
        # From must be the SMTP user, To must be the applicant
        assert args[0] == "user@example.com"
        assert args[1] == "alice@example.com"

    def test_email_subject_contains_job_title(self, db_session: Session) -> None:
        from app.services.email_service import send_application_confirmation

        app_id = _seed_application(db_session)

        with patch("app.services.email_service.get_settings", return_value=_make_settings()):
            with patch("smtplib.SMTP") as mock_smtp_cls:
                mock_smtp = MagicMock()
                mock_smtp_cls.return_value.__enter__ = lambda s: mock_smtp
                mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
                send_application_confirmation(app_id, _db=db_session)

        raw_message = mock_smtp.sendmail.call_args[0][2]
        assert "Dev" in raw_message  # job title from _seed_application

    def test_skips_when_notifications_disabled(self, db_session: Session) -> None:
        from app.services.email_service import send_application_confirmation

        app_id = _seed_application(db_session)

        with patch(
            "app.services.email_service.get_settings",
            return_value=_make_settings(NOTIFICATIONS_ENABLED=False),
        ):
            with patch("smtplib.SMTP") as mock_smtp_cls:
                send_application_confirmation(app_id, _db=db_session)
                mock_smtp_cls.assert_not_called()

    def test_skips_when_smtp_host_missing(self, db_session: Session) -> None:
        from app.services.email_service import send_application_confirmation

        app_id = _seed_application(db_session)

        with patch(
            "app.services.email_service.get_settings",
            return_value=_make_settings(SMTP_HOST=None),
        ):
            with patch("smtplib.SMTP") as mock_smtp_cls:
                send_application_confirmation(app_id, _db=db_session)
                mock_smtp_cls.assert_not_called()

    def test_skips_when_application_not_found(self, db_session: Session) -> None:
        from app.services.email_service import send_application_confirmation

        with patch("app.services.email_service.get_settings", return_value=_make_settings()):
            with patch("smtplib.SMTP") as mock_smtp_cls:
                send_application_confirmation("nonexistent-id", _db=db_session)
                mock_smtp_cls.assert_not_called()

    def test_does_not_raise_on_smtp_failure(self, db_session: Session) -> None:
        from app.services.email_service import send_application_confirmation

        app_id = _seed_application(db_session)

        with patch("app.services.email_service.get_settings", return_value=_make_settings()):
            with patch("smtplib.SMTP", side_effect=ConnectionRefusedError("refused")):
                send_application_confirmation(app_id, _db=db_session)

    def test_both_background_tasks_triggered_on_apply(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """Integration: POST /jobs/{id}/apply enqueues both the admin notification and applicant confirmation."""
        from io import BytesIO

        job_resp = client.post(ADMIN_JOBS_URL, json=BASE_JOB, headers=auth_headers)
        job_id = job_resp.json()["public_id"]

        with patch(
            "app.services.email_service.send_new_application_notification"
        ) as mock_notify, patch(
            "app.services.email_service.send_application_confirmation"
        ) as mock_confirm:
            resp = client.post(
                PUBLIC_APPLY_URL.format(job_id=job_id),
                data={"applicant_name": "Bob", "applicant_email": "bob@x.com", "responses_json": "{}"},
                files={"cv_file": ("cv.pdf", BytesIO(b"%PDF fake"), "application/pdf")},
            )
            assert resp.status_code == 201
            mock_notify.assert_called_once()
            mock_confirm.assert_called_once()
