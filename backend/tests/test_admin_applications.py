"""
Tests for the admin applications endpoints:
  GET  /api/v1/admin/applications
  GET  /api/v1/admin/applications/{id}
  PATCH /api/v1/admin/applications/{id}/status
"""
from __future__ import annotations

import json
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

_FAKE_PDF = b"%PDF-1.4 fake"


def _apply(
    client: TestClient,
    job_public_id: str,
    *,
    name: str = "Jane Doe",
    email: str = "jane@example.com",
) -> "Response":  # type: ignore[name-defined]
    data = {"applicant_name": name, "applicant_email": email, "responses_json": "{}"}
    files = {"cv_file": ("cv.pdf", BytesIO(_FAKE_PDF), "application/pdf")}
    return client.post(f"/api/v1/jobs/{job_public_id}/apply", data=data, files=files)

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ADMIN_JOBS_URL = "/api/v1/admin/jobs"
ADMIN_APPS_URL = "/api/v1/admin/applications"

ADMIN = {
    "email": "admin@example.com",
    "display_name": "Test Admin",
    "password": "securepassword123",
}

BASE_JOB = {
    "title": "Python Developer",
    "description": "<p>Great role.</p>",
    "employment_type": "full_time",
    "location": "Remote",
    "is_remote": True,
    "application_mode": "form",
    "external_apply_url": None,
    "tags": [],
    "expires_at": None,
}

APPLICANT_A = {
    "applicant_name": "Alice Smith",
    "applicant_email": "alice@example.com",
    "responses": {},
}

APPLICANT_B = {
    "applicant_name": "Bob Jones",
    "applicant_email": "bob@example.com",
    "responses": {},
}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def auth_headers(client: TestClient) -> dict:
    client.post(REGISTER_URL, json=ADMIN)
    resp = client.post(LOGIN_URL, json={"email": ADMIN["email"], "password": ADMIN["password"]})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture()
def job(client: TestClient, auth_headers: dict) -> dict:
    resp = client.post(ADMIN_JOBS_URL, json=BASE_JOB, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture()
def submitted_application(client: TestClient, job: dict) -> dict:
    """Submit one application and return the confirmation payload."""
    resp = _apply(client, job["public_id"], name=APPLICANT_A["applicant_name"], email=APPLICANT_A["applicant_email"])
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture()
def two_applications(client: TestClient, job: dict) -> list[dict]:
    """Submit two applications and return both confirmation payloads."""
    r1 = _apply(client, job["public_id"], name=APPLICANT_A["applicant_name"], email=APPLICANT_A["applicant_email"])
    r2 = _apply(client, job["public_id"], name=APPLICANT_B["applicant_name"], email=APPLICANT_B["applicant_email"])
    assert r1.status_code == 201
    assert r2.status_code == 201
    return [r1.json(), r2.json()]


# ── GET /admin/applications — list ────────────────────────────────────────────

class TestListApplications:
    def test_returns_empty_list_when_no_applications(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        resp = client.get(ADMIN_APPS_URL, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["page"] == 1

    def test_returns_submitted_applications(
        self, client: TestClient, auth_headers: dict, two_applications: list
    ) -> None:
        resp = client.get(ADMIN_APPS_URL, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert len(body["items"]) == 2

    def test_response_shape(
        self, client: TestClient, auth_headers: dict, submitted_application: dict
    ) -> None:
        resp = client.get(ADMIN_APPS_URL, headers=auth_headers)
        item = resp.json()["items"][0]
        assert "public_id" in item
        assert "applicant_name" in item
        assert "applicant_email" in item
        assert "status" in item
        assert "created_at" in item
        assert "job_public_id" in item
        assert "job_title" in item
        assert item["status"] == "new"
        assert item["applicant_name"] == APPLICANT_A["applicant_name"]

    def test_filter_by_job_id(
        self, client: TestClient, auth_headers: dict, job: dict, two_applications: list
    ) -> None:
        # Create a second job with no applications
        resp2 = client.post(
            ADMIN_JOBS_URL,
            json={**BASE_JOB, "title": "Other Job"},
            headers=auth_headers,
        )
        second_job_id = resp2.json()["public_id"]

        # Filter by first job — should return 2
        resp = client.get(
            ADMIN_APPS_URL, params={"job_id": job["public_id"]}, headers=auth_headers
        )
        assert resp.json()["total"] == 2

        # Filter by second job — should return 0
        resp = client.get(
            ADMIN_APPS_URL, params={"job_id": second_job_id}, headers=auth_headers
        )
        assert resp.json()["total"] == 0

    def test_filter_by_status(
        self, client: TestClient, auth_headers: dict, two_applications: list
    ) -> None:
        app_id = two_applications[0]["public_id"]
        # Update first application to "reviewed"
        client.patch(
            f"{ADMIN_APPS_URL}/{app_id}/status",
            json={"status": "reviewed"},
            headers=auth_headers,
        )

        resp_new = client.get(
            ADMIN_APPS_URL, params={"status": "new"}, headers=auth_headers
        )
        resp_reviewed = client.get(
            ADMIN_APPS_URL, params={"status": "reviewed"}, headers=auth_headers
        )
        assert resp_new.json()["total"] == 1
        assert resp_reviewed.json()["total"] == 1

    def test_pagination(
        self, client: TestClient, auth_headers: dict, two_applications: list
    ) -> None:
        resp = client.get(
            ADMIN_APPS_URL, params={"page": 1, "per_page": 1}, headers=auth_headers
        )
        body = resp.json()
        assert body["total"] == 2
        assert len(body["items"]) == 1
        assert body["pages"] == 2

    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.get(ADMIN_APPS_URL)
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, client: TestClient) -> None:
        resp = client.get(ADMIN_APPS_URL, headers={"Authorization": "Bearer bad.token"})
        assert resp.status_code == 401


# ── GET /admin/applications/{id} — detail ─────────────────────────────────────

class TestGetApplication:
    def test_returns_full_detail(
        self, client: TestClient, auth_headers: dict, submitted_application: dict
    ) -> None:
        app_id = submitted_application["public_id"]
        resp = client.get(f"{ADMIN_APPS_URL}/{app_id}", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["public_id"] == app_id
        assert body["applicant_name"] == APPLICANT_A["applicant_name"]
        assert body["applicant_email"] == APPLICANT_A["applicant_email"].lower()
        assert body["status"] == "new"
        assert "responses" in body
        assert "job_public_id" in body
        assert "job_title" in body

    def test_unknown_id_returns_404(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        resp = client.get(
            f"{ADMIN_APPS_URL}/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_requires_auth(
        self, client: TestClient, submitted_application: dict
    ) -> None:
        app_id = submitted_application["public_id"]
        resp = client.get(f"{ADMIN_APPS_URL}/{app_id}")
        assert resp.status_code == 401


# ── PATCH /admin/applications/{id}/status ─────────────────────────────────────

class TestUpdateApplicationStatus:
    def test_update_to_reviewed(
        self, client: TestClient, auth_headers: dict, submitted_application: dict
    ) -> None:
        app_id = submitted_application["public_id"]
        resp = client.patch(
            f"{ADMIN_APPS_URL}/{app_id}/status",
            json={"status": "reviewed"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "reviewed"

    def test_update_to_rejected(
        self, client: TestClient, auth_headers: dict, submitted_application: dict
    ) -> None:
        app_id = submitted_application["public_id"]
        resp = client.patch(
            f"{ADMIN_APPS_URL}/{app_id}/status",
            json={"status": "rejected"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    def test_update_to_hired(
        self, client: TestClient, auth_headers: dict, submitted_application: dict
    ) -> None:
        app_id = submitted_application["public_id"]
        resp = client.patch(
            f"{ADMIN_APPS_URL}/{app_id}/status",
            json={"status": "hired"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "hired"

    def test_status_persisted_after_update(
        self, client: TestClient, auth_headers: dict, submitted_application: dict
    ) -> None:
        app_id = submitted_application["public_id"]
        client.patch(
            f"{ADMIN_APPS_URL}/{app_id}/status",
            json={"status": "hired"},
            headers=auth_headers,
        )
        resp = client.get(f"{ADMIN_APPS_URL}/{app_id}", headers=auth_headers)
        assert resp.json()["status"] == "hired"

    def test_invalid_status_returns_422(
        self, client: TestClient, auth_headers: dict, submitted_application: dict
    ) -> None:
        app_id = submitted_application["public_id"]
        resp = client.patch(
            f"{ADMIN_APPS_URL}/{app_id}/status",
            json={"status": "bogus_status"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_missing_status_field_returns_422(
        self, client: TestClient, auth_headers: dict, submitted_application: dict
    ) -> None:
        app_id = submitted_application["public_id"]
        resp = client.patch(
            f"{ADMIN_APPS_URL}/{app_id}/status",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_unknown_id_returns_404(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        resp = client.patch(
            f"{ADMIN_APPS_URL}/00000000-0000-0000-0000-000000000000/status",
            json={"status": "reviewed"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_requires_auth(
        self, client: TestClient, submitted_application: dict
    ) -> None:
        app_id = submitted_application["public_id"]
        resp = client.patch(
            f"{ADMIN_APPS_URL}/{app_id}/status", json={"status": "reviewed"}
        )
        assert resp.status_code == 401
