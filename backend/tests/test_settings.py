"""
Tests for POST /api/v1/admin/settings/test-email
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
TEST_EMAIL_URL = "/api/v1/admin/settings/test-email"

ADMIN = {
    "email": "admin@example.com",
    "display_name": "Test Admin",
    "password": "securepassword123",
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


@pytest.fixture()
def auth_headers(client: TestClient) -> dict:
    client.post(REGISTER_URL, json=ADMIN)
    resp = client.post(LOGIN_URL, json={"email": ADMIN["email"], "password": ADMIN["password"]})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _make_settings(**overrides):
    from app.config import Settings

    defaults = FULL_SMTP_SETTINGS.copy()
    defaults.update(overrides)
    s = MagicMock(spec=Settings)
    for k, v in defaults.items():
        setattr(s, k, v)
    return s


class TestTestEmailEndpoint:
    def test_sends_email_and_returns_success(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        with patch(
            "app.services.email_service.get_settings", return_value=_make_settings()
        ):
            with patch("smtplib.SMTP") as mock_smtp_cls:
                mock_smtp = MagicMock()
                mock_smtp_cls.return_value.__enter__ = lambda s: mock_smtp
                mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

                resp = client.post(
                    TEST_EMAIL_URL,
                    json={"to": "recipient@example.com"},
                    headers=auth_headers,
                )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        mock_smtp.sendmail.assert_called_once()
        _, to_addr, _ = mock_smtp.sendmail.call_args[0]
        assert to_addr == "recipient@example.com"

    def test_returns_failure_when_smtp_config_missing(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        with patch(
            "app.services.email_service.get_settings",
            return_value=_make_settings(SMTP_HOST=None),
        ):
            resp = client.post(
                TEST_EMAIL_URL,
                json={"to": "recipient@example.com"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert "SMTP_HOST" in body["message"]

    def test_returns_failure_on_smtp_error(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        with patch(
            "app.services.email_service.get_settings", return_value=_make_settings()
        ):
            with patch("smtplib.SMTP", side_effect=ConnectionRefusedError("refused")):
                resp = client.post(
                    TEST_EMAIL_URL,
                    json={"to": "recipient@example.com"},
                    headers=auth_headers,
                )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert "refused" in body["message"]

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.post(TEST_EMAIL_URL, json={"to": "recipient@example.com"})
        assert resp.status_code == 401

    def test_rejects_invalid_email(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        resp = client.post(
            TEST_EMAIL_URL,
            json={"to": "not-an-email"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_rejects_missing_to_field(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        resp = client.post(TEST_EMAIL_URL, json={}, headers=auth_headers)
        assert resp.status_code == 422
