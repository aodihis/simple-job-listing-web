"""
Tests for POST /api/v1/auth/register, POST /api/v1/auth/login,
POST /api/v1/auth/refresh, GET /api/v1/auth/me.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
REFRESH_URL = "/api/v1/auth/refresh"
ME_URL = "/api/v1/auth/me"

ADMIN_DATA = {
    "email": "admin@example.com",
    "display_name": "Test Admin",
    "password": "securepassword123",
}


class TestRegister:
    def test_register_first_admin_returns_token(self, client: TestClient) -> None:
        response = client.post(REGISTER_URL, json=ADMIN_DATA)
        assert response.status_code == 201
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] > 0

    def test_register_fails_when_admin_already_exists(self, client: TestClient) -> None:
        client.post(REGISTER_URL, json=ADMIN_DATA)
        response = client.post(REGISTER_URL, json=ADMIN_DATA)
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_register_fails_with_short_password(self, client: TestClient) -> None:
        response = client.post(
            REGISTER_URL,
            json={**ADMIN_DATA, "password": "short"},
        )
        assert response.status_code == 422

    def test_register_fails_with_invalid_email(self, client: TestClient) -> None:
        response = client.post(
            REGISTER_URL,
            json={**ADMIN_DATA, "email": "not-an-email"},
        )
        assert response.status_code == 422


class TestLogin:
    @pytest.fixture(autouse=True)
    def create_admin(self, client: TestClient) -> None:
        client.post(REGISTER_URL, json=ADMIN_DATA)

    def test_login_success_returns_token(self, client: TestClient) -> None:
        response = client.post(
            LOGIN_URL,
            json={"email": ADMIN_DATA["email"], "password": ADMIN_DATA["password"]},
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    def test_login_fails_with_wrong_password(self, client: TestClient) -> None:
        response = client.post(
            LOGIN_URL,
            json={"email": ADMIN_DATA["email"], "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"]

    def test_login_fails_with_unknown_email(self, client: TestClient) -> None:
        response = client.post(
            LOGIN_URL,
            json={"email": "nobody@example.com", "password": "somepassword"},
        )
        assert response.status_code == 401

    def test_login_fails_with_invalid_email_format(self, client: TestClient) -> None:
        response = client.post(
            LOGIN_URL,
            json={"email": "not-valid", "password": "somepassword"},
        )
        assert response.status_code == 422


class TestMe:
    @pytest.fixture()
    def auth_headers(self, client: TestClient) -> dict:
        client.post(REGISTER_URL, json=ADMIN_DATA)
        resp = client.post(
            LOGIN_URL,
            json={"email": ADMIN_DATA["email"], "password": ADMIN_DATA["password"]},
        )
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_me_returns_current_user(self, client: TestClient, auth_headers: dict) -> None:
        response = client.get(ME_URL, headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["email"] == ADMIN_DATA["email"]
        assert body["display_name"] == ADMIN_DATA["display_name"]
        assert "public_id" in body

    def test_me_fails_without_token(self, client: TestClient) -> None:
        response = client.get(ME_URL)
        assert response.status_code == 401

    def test_me_fails_with_invalid_token(self, client: TestClient) -> None:
        response = client.get(ME_URL, headers={"Authorization": "Bearer invalid.token.here"})
        assert response.status_code == 401

    def test_me_fails_with_malformed_header(self, client: TestClient) -> None:
        response = client.get(ME_URL, headers={"Authorization": "NotBearer token"})
        assert response.status_code == 401


class TestRefresh:
    @pytest.fixture(autouse=True)
    def create_admin(self, client: TestClient) -> None:
        client.post(REGISTER_URL, json=ADMIN_DATA)

    def _login(self, client: TestClient) -> dict:
        resp = client.post(
            LOGIN_URL,
            json={"email": ADMIN_DATA["email"], "password": ADMIN_DATA["password"]},
        )
        return resp.json()

    def test_refresh_returns_new_tokens(self, client: TestClient) -> None:
        tokens = self._login(client)
        response = client.post(REFRESH_URL, json={"refresh_token": tokens["refresh_token"]})
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] > 0

    def test_refresh_token_is_rotated(self, client: TestClient) -> None:
        """Each refresh issues a new refresh token; the old one must not work again."""
        tokens = self._login(client)
        old_rt = tokens["refresh_token"]

        resp = client.post(REFRESH_URL, json={"refresh_token": old_rt})
        assert resp.status_code == 200

        # Reusing the old refresh token must fail
        resp2 = client.post(REFRESH_URL, json={"refresh_token": old_rt})
        assert resp2.status_code == 401

    def test_new_access_token_is_valid(self, client: TestClient) -> None:
        tokens = self._login(client)
        refresh_resp = client.post(REFRESH_URL, json={"refresh_token": tokens["refresh_token"]})
        new_access_token = refresh_resp.json()["access_token"]

        me_resp = client.get(ME_URL, headers={"Authorization": f"Bearer {new_access_token}"})
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == ADMIN_DATA["email"]

    def test_refresh_fails_with_invalid_token(self, client: TestClient) -> None:
        response = client.post(REFRESH_URL, json={"refresh_token": "this-is-not-a-valid-token"})
        assert response.status_code == 401

    def test_refresh_fails_with_missing_token(self, client: TestClient) -> None:
        response = client.post(REFRESH_URL, json={})
        assert response.status_code == 422
