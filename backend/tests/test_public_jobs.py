"""
Tests for the public job endpoints (no auth required):

  GET /api/v1/jobs           — list active jobs with filters
  GET /api/v1/jobs/{id}      — single job detail
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ADMIN_JOBS_URL = "/api/v1/admin/jobs"
PUBLIC_JOBS_URL = "/api/v1/jobs"

ADMIN = {
    "email": "admin@example.com",
    "display_name": "Test Admin",
    "password": "securepassword123",
}

BASE_JOB = {
    "title": "Backend Engineer",
    "description": "<p>Build great things.</p>",
    "employment_type": "full_time",
    "location": "New York",
    "is_remote": False,
    "application_mode": "form",
    "external_apply_url": None,
    "tags": ["python"],
    "expires_at": None,
}


# ── Shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture()
def auth_headers(client: TestClient) -> dict:
    client.post(REGISTER_URL, json=ADMIN)
    resp = client.post(LOGIN_URL, json={"email": ADMIN["email"], "password": ADMIN["password"]})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _create_job(client: TestClient, headers: dict, overrides: dict | None = None) -> dict:
    payload = {**BASE_JOB, **(overrides or {})}
    resp = client.post(ADMIN_JOBS_URL, json=payload, headers=headers)
    assert resp.status_code == 201
    return resp.json()


# ── GET /api/v1/jobs ──────────────────────────────────────────────────────────

class TestListPublicJobs:
    def test_returns_active_jobs(self, client: TestClient, auth_headers: dict) -> None:
        _create_job(client, auth_headers)
        resp = client.get(PUBLIC_JOBS_URL)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert all(i["employment_type"] for i in body["items"])

    def test_excludes_inactive_jobs(self, client: TestClient, auth_headers: dict) -> None:
        job = _create_job(client, auth_headers)
        # deactivate
        client.patch(f"{ADMIN_JOBS_URL}/{job['public_id']}/toggle", headers=auth_headers)
        resp = client.get(PUBLIC_JOBS_URL)
        ids = [j["public_id"] for j in resp.json()["items"]]
        assert job["public_id"] not in ids

    def test_excludes_deleted_jobs(self, client: TestClient, auth_headers: dict) -> None:
        job = _create_job(client, auth_headers)
        client.delete(f"{ADMIN_JOBS_URL}/{job['public_id']}", headers=auth_headers)
        resp = client.get(PUBLIC_JOBS_URL)
        ids = [j["public_id"] for j in resp.json()["items"]]
        assert job["public_id"] not in ids

    def test_excludes_expired_jobs(self, client: TestClient, auth_headers: dict) -> None:
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        job = _create_job(client, auth_headers, {"expires_at": past})
        resp = client.get(PUBLIC_JOBS_URL)
        ids = [j["public_id"] for j in resp.json()["items"]]
        assert job["public_id"] not in ids

    def test_includes_non_expired_jobs(self, client: TestClient, auth_headers: dict) -> None:
        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        job = _create_job(client, auth_headers, {"expires_at": future})
        resp = client.get(PUBLIC_JOBS_URL)
        ids = [j["public_id"] for j in resp.json()["items"]]
        assert job["public_id"] in ids

    def test_filter_by_employment_type(self, client: TestClient, auth_headers: dict) -> None:
        _create_job(client, auth_headers, {"title": "FT Job", "employment_type": "full_time"})
        _create_job(client, auth_headers, {"title": "PT Job", "employment_type": "part_time"})
        resp = client.get(f"{PUBLIC_JOBS_URL}?employment_type=part_time")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(j["employment_type"] == "part_time" for j in items)
        assert any(j["title"] == "PT Job" for j in items)

    def test_filter_by_is_remote(self, client: TestClient, auth_headers: dict) -> None:
        _create_job(client, auth_headers, {"title": "Remote Job", "is_remote": True})
        _create_job(client, auth_headers, {"title": "Onsite Job", "is_remote": False})
        resp = client.get(f"{PUBLIC_JOBS_URL}?is_remote=true")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(j["is_remote"] for j in items)

    def test_filter_by_tag(self, client: TestClient, auth_headers: dict) -> None:
        _create_job(client, auth_headers, {"title": "Python Job", "tags": ["python", "django"]})
        _create_job(client, auth_headers, {"title": "Go Job", "tags": ["go"]})
        resp = client.get(f"{PUBLIC_JOBS_URL}?tags=django")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(any(t["name"] == "django" for t in j["tags"]) for j in items)

    def test_search_by_title(self, client: TestClient, auth_headers: dict) -> None:
        _create_job(client, auth_headers, {"title": "Unique Zebra Engineer"})
        _create_job(client, auth_headers, {"title": "Generic Role"})
        resp = client.get(f"{PUBLIC_JOBS_URL}?q=Zebra")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert any("Zebra" in j["title"] for j in items)
        assert all("Zebra" in j["title"] or "zebra" in j["title"] for j in items)

    def test_search_by_description(self, client: TestClient, auth_headers: dict) -> None:
        _create_job(client, auth_headers, {
            "title": "Role A",
            "description": "<p>Requires knowledge of astrophysics.</p>",
        })
        _create_job(client, auth_headers, {
            "title": "Role B",
            "description": "<p>Normal job description.</p>",
        })
        resp = client.get(f"{PUBLIC_JOBS_URL}?q=astrophysics")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_sort_newest(self, client: TestClient, auth_headers: dict) -> None:
        import time
        _create_job(client, auth_headers, {"title": "First"})
        time.sleep(1.1)  # SQLite CURRENT_TIMESTAMP has second precision
        _create_job(client, auth_headers, {"title": "Second"})
        resp = client.get(f"{PUBLIC_JOBS_URL}?sort=newest")
        assert resp.status_code == 200
        titles = [j["title"] for j in resp.json()["items"]]
        # "Second" was created last, should appear first
        assert titles.index("Second") < titles.index("First")

    def test_sort_oldest(self, client: TestClient, auth_headers: dict) -> None:
        import time
        _create_job(client, auth_headers, {"title": "First"})
        time.sleep(1.1)  # SQLite CURRENT_TIMESTAMP has second precision
        _create_job(client, auth_headers, {"title": "Second"})
        resp = client.get(f"{PUBLIC_JOBS_URL}?sort=oldest")
        assert resp.status_code == 200
        titles = [j["title"] for j in resp.json()["items"]]
        assert titles.index("First") < titles.index("Second")

    def test_pagination(self, client: TestClient, auth_headers: dict) -> None:
        for i in range(4):
            _create_job(client, auth_headers, {"title": f"Job {i}"})
        resp = client.get(f"{PUBLIC_JOBS_URL}?page=1&per_page=2")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 2
        assert body["total"] >= 4
        assert body["pages"] >= 2

    def test_response_does_not_include_admin_fields(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        _create_job(client, auth_headers)
        resp = client.get(PUBLIC_JOBS_URL)
        item = resp.json()["items"][0]
        assert "is_active" not in item
        assert "is_deleted" not in item
        assert "posted_by_email" not in item

    def test_empty_list_returns_zero_total(self, client: TestClient) -> None:
        resp = client.get(PUBLIC_JOBS_URL)
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


# ── GET /api/v1/jobs/{id} ─────────────────────────────────────────────────────

class TestGetPublicJob:
    def test_returns_full_job_detail(self, client: TestClient, auth_headers: dict) -> None:
        job = _create_job(client, auth_headers)
        resp = client.get(f"{PUBLIC_JOBS_URL}/{job['public_id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["public_id"] == job["public_id"]
        assert body["description"] == BASE_JOB["description"]
        assert "application_mode" in body
        assert "form_fields" in body

    def test_not_found_returns_404(self, client: TestClient) -> None:
        resp = client.get(f"{PUBLIC_JOBS_URL}/no-such-id")
        assert resp.status_code == 404

    def test_inactive_job_returns_404(self, client: TestClient, auth_headers: dict) -> None:
        job = _create_job(client, auth_headers)
        client.patch(f"{ADMIN_JOBS_URL}/{job['public_id']}/toggle", headers=auth_headers)
        resp = client.get(f"{PUBLIC_JOBS_URL}/{job['public_id']}")
        assert resp.status_code == 404

    def test_deleted_job_returns_404(self, client: TestClient, auth_headers: dict) -> None:
        job = _create_job(client, auth_headers)
        client.delete(f"{ADMIN_JOBS_URL}/{job['public_id']}", headers=auth_headers)
        resp = client.get(f"{PUBLIC_JOBS_URL}/{job['public_id']}")
        assert resp.status_code == 404

    def test_expired_job_returns_404(self, client: TestClient, auth_headers: dict) -> None:
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        job = _create_job(client, auth_headers, {"expires_at": past})
        resp = client.get(f"{PUBLIC_JOBS_URL}/{job['public_id']}")
        assert resp.status_code == 404

    def test_response_does_not_include_admin_fields(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        job = _create_job(client, auth_headers)
        resp = client.get(f"{PUBLIC_JOBS_URL}/{job['public_id']}")
        body = resp.json()
        assert "is_active" not in body
        assert "is_deleted" not in body
        assert "posted_by_email" not in body

    def test_no_auth_required(self, client: TestClient, auth_headers: dict) -> None:
        """Public endpoints must work without any Authorization header."""
        job = _create_job(client, auth_headers)
        resp = client.get(f"{PUBLIC_JOBS_URL}/{job['public_id']}")
        assert resp.status_code == 200
