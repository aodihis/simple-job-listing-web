"""
Tests for the admin job endpoints:

  POST   /api/v1/admin/jobs
  GET    /api/v1/admin/jobs
  GET    /api/v1/admin/jobs/{id}
  PATCH  /api/v1/admin/jobs/{id}/toggle
  DELETE /api/v1/admin/jobs/{id}
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
JOBS_URL = "/api/v1/admin/jobs"

ADMIN = {
    "email": "admin@example.com",
    "display_name": "Test Admin",
    "password": "securepassword123",
}

JOB_PAYLOAD = {
    "title": "Backend Engineer",
    "description": "<p>Build things.</p>",
    "employment_type": "full_time",
    "location": "Remote",
    "is_remote": True,
    "application_mode": "form",
    "external_apply_url": None,
    "tags": ["python", "fastapi"],
    "expires_at": None,
}


# ── Shared fixture ────────────────────────────────────────────────────────────

@pytest.fixture()
def auth_headers(client: TestClient) -> dict:
    client.post(REGISTER_URL, json=ADMIN)
    resp = client.post(LOGIN_URL, json={"email": ADMIN["email"], "password": ADMIN["password"]})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture()
def created_job(client: TestClient, auth_headers: dict) -> dict:
    resp = client.post(JOBS_URL, json=JOB_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()


# ── POST /api/v1/admin/jobs ───────────────────────────────────────────────────

class TestCreateJob:
    def test_create_returns_201_with_job(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.post(JOBS_URL, json=JOB_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == JOB_PAYLOAD["title"]
        assert body["employment_type"] == "full_time"
        assert body["is_active"] is True
        assert body["is_deleted"] is False
        assert "public_id" in body
        assert any(t["name"] == "python" for t in body["tags"])
        assert any(t["name"] == "fastapi" for t in body["tags"])
        assert body["form_fields"] == []

    def test_create_normalises_tags_to_lowercase(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        payload = {**JOB_PAYLOAD, "tags": ["Python", "  FastAPI  "]}
        resp = client.post(JOBS_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 201
        names = [t["name"] for t in resp.json()["tags"]]
        assert "python" in names
        assert "fastapi" in names

    def test_create_external_url_job(self, client: TestClient, auth_headers: dict) -> None:
        payload = {
            **JOB_PAYLOAD,
            "application_mode": "external_url",
            "external_apply_url": "https://apply.example.com/jobs/1",
        }
        resp = client.post(JOBS_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 201
        body = resp.json()
        assert body["application_mode"] == "external_url"
        assert body["external_apply_url"] == "https://apply.example.com/jobs/1"

    def test_create_external_url_requires_url(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        payload = {
            **JOB_PAYLOAD,
            "application_mode": "external_url",
            "external_apply_url": None,
        }
        resp = client.post(JOBS_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 422

    def test_create_invalid_employment_type_rejected(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        payload = {**JOB_PAYLOAD, "employment_type": "unicorn"}
        resp = client.post(JOBS_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 422

    def test_create_empty_title_rejected(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        payload = {**JOB_PAYLOAD, "title": ""}
        resp = client.post(JOBS_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 422

    def test_create_requires_auth(self, client: TestClient) -> None:
        resp = client.post(JOBS_URL, json=JOB_PAYLOAD)
        assert resp.status_code == 401


# ── GET /api/v1/admin/jobs ────────────────────────────────────────────────────

class TestListJobs:
    def test_list_returns_paginated_response(
        self, client: TestClient, auth_headers: dict, created_job: dict
    ) -> None:
        resp = client.get(JOBS_URL, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert body["total"] >= 1
        assert any(j["public_id"] == created_job["public_id"] for j in body["items"])

    def test_list_excludes_deleted_by_default(
        self, client: TestClient, auth_headers: dict, created_job: dict
    ) -> None:
        client.delete(f"{JOBS_URL}/{created_job['public_id']}", headers=auth_headers)
        resp = client.get(JOBS_URL, headers=auth_headers)
        assert resp.status_code == 200
        ids = [j["public_id"] for j in resp.json()["items"]]
        assert created_job["public_id"] not in ids

    def test_list_includes_deleted_when_requested(
        self, client: TestClient, auth_headers: dict, created_job: dict
    ) -> None:
        client.delete(f"{JOBS_URL}/{created_job['public_id']}", headers=auth_headers)
        resp = client.get(f"{JOBS_URL}?include_deleted=true", headers=auth_headers)
        assert resp.status_code == 200
        ids = [j["public_id"] for j in resp.json()["items"]]
        assert created_job["public_id"] in ids

    def test_list_pagination(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        for i in range(3):
            client.post(JOBS_URL, json={**JOB_PAYLOAD, "title": f"Job {i}"}, headers=auth_headers)
        resp = client.get(f"{JOBS_URL}?page=1&per_page=2", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 2
        assert body["total"] >= 3
        assert body["pages"] >= 2

    def test_list_requires_auth(self, client: TestClient) -> None:
        resp = client.get(JOBS_URL)
        assert resp.status_code == 401


# ── GET /api/v1/admin/jobs/{id} ───────────────────────────────────────────────

class TestGetJob:
    def test_get_returns_full_job(
        self, client: TestClient, auth_headers: dict, created_job: dict
    ) -> None:
        resp = client.get(f"{JOBS_URL}/{created_job['public_id']}", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["public_id"] == created_job["public_id"]
        assert body["description"] == JOB_PAYLOAD["description"]
        assert "posted_by_email" in body
        assert body["form_fields"] == []

    def test_get_not_found(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.get(f"{JOBS_URL}/no-such-id", headers=auth_headers)
        assert resp.status_code == 404

    def test_get_deleted_job_returns_404(
        self, client: TestClient, auth_headers: dict, created_job: dict
    ) -> None:
        client.delete(f"{JOBS_URL}/{created_job['public_id']}", headers=auth_headers)
        resp = client.get(f"{JOBS_URL}/{created_job['public_id']}", headers=auth_headers)
        assert resp.status_code == 404

    def test_get_requires_auth(self, client: TestClient, created_job: dict) -> None:
        resp = client.get(f"{JOBS_URL}/{created_job['public_id']}")
        assert resp.status_code == 401


# ── PATCH /api/v1/admin/jobs/{id}/toggle ─────────────────────────────────────

class TestToggleJob:
    def test_toggle_deactivates_active_job(
        self, client: TestClient, auth_headers: dict, created_job: dict
    ) -> None:
        assert created_job["is_active"] is True
        resp = client.patch(
            f"{JOBS_URL}/{created_job['public_id']}/toggle", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_toggle_reactivates_inactive_job(
        self, client: TestClient, auth_headers: dict, created_job: dict
    ) -> None:
        pid = created_job["public_id"]
        client.patch(f"{JOBS_URL}/{pid}/toggle", headers=auth_headers)
        resp = client.patch(f"{JOBS_URL}/{pid}/toggle", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True

    def test_toggle_not_found(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.patch(f"{JOBS_URL}/no-such-id/toggle", headers=auth_headers)
        assert resp.status_code == 404

    def test_toggle_requires_auth(self, client: TestClient, created_job: dict) -> None:
        resp = client.patch(f"{JOBS_URL}/{created_job['public_id']}/toggle")
        assert resp.status_code == 401


# ── DELETE /api/v1/admin/jobs/{id} ───────────────────────────────────────────

class TestDeleteJob:
    def test_delete_soft_deletes_job(
        self, client: TestClient, auth_headers: dict, created_job: dict
    ) -> None:
        resp = client.delete(
            f"{JOBS_URL}/{created_job['public_id']}", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["is_deleted"] is True
        assert body["is_active"] is False

    def test_delete_removes_from_list(
        self, client: TestClient, auth_headers: dict, created_job: dict
    ) -> None:
        client.delete(f"{JOBS_URL}/{created_job['public_id']}", headers=auth_headers)
        list_resp = client.get(JOBS_URL, headers=auth_headers)
        ids = [j["public_id"] for j in list_resp.json()["items"]]
        assert created_job["public_id"] not in ids

    def test_delete_already_deleted_returns_404(
        self, client: TestClient, auth_headers: dict, created_job: dict
    ) -> None:
        pid = created_job["public_id"]
        client.delete(f"{JOBS_URL}/{pid}", headers=auth_headers)
        resp = client.delete(f"{JOBS_URL}/{pid}", headers=auth_headers)
        assert resp.status_code == 404

    def test_delete_not_found(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.delete(f"{JOBS_URL}/no-such-id", headers=auth_headers)
        assert resp.status_code == 404

    def test_delete_requires_auth(self, client: TestClient, created_job: dict) -> None:
        resp = client.delete(f"{JOBS_URL}/{created_job['public_id']}")
        assert resp.status_code == 401
