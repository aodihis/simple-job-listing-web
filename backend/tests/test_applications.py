"""
Tests for POST /api/v1/jobs/{id}/apply — public application submission.
Covers happy path, field validation, duplicate prevention, and job-state guards.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ADMIN_JOBS_URL = "/api/v1/admin/jobs"

ADMIN = {
    "email": "admin@example.com",
    "display_name": "Test Admin",
    "password": "securepassword123",
}

BASE_JOB = {
    "title": "Python Developer",
    "description": "<p>Great opportunity.</p>",
    "employment_type": "full_time",
    "location": "Remote",
    "is_remote": True,
    "application_mode": "form",
    "external_apply_url": None,
    "tags": [],
    "expires_at": None,
}

APPLICANT = {
    "applicant_name": "Jane Doe",
    "applicant_email": "jane@example.com",
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


def apply_url(job_public_id: str) -> str:
    return f"/api/v1/jobs/{job_public_id}/apply"


def set_form_fields(client: TestClient, headers: dict, job_id: str, fields: list) -> None:
    resp = client.put(
        f"{ADMIN_JOBS_URL}/{job_id}/form-fields",
        json={"fields": fields},
        headers=headers,
    )
    assert resp.status_code == 200


# ── Happy path ────────────────────────────────────────────────────────────────

class TestSubmitApplication:
    def test_submit_with_no_form_fields_returns_201(
        self, client: TestClient, job: dict
    ) -> None:
        resp = client.post(apply_url(job["public_id"]), json=APPLICANT)
        assert resp.status_code == 201
        body = resp.json()
        assert "public_id" in body
        assert "message" in body

    def test_submit_stores_lowercase_email(
        self, client: TestClient, job: dict
    ) -> None:
        payload = {**APPLICANT, "applicant_email": "Jane@Example.COM"}
        resp = client.post(apply_url(job["public_id"]), json=payload)
        assert resp.status_code == 201

    def test_submit_with_text_field(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        fields = client.put(
            f"{ADMIN_JOBS_URL}/{job['public_id']}/form-fields",
            json={"fields": [{"label": "Cover letter", "field_type": "textarea",
                               "is_required": True, "options": []}]},
            headers=auth_headers,
        ).json()
        field_id = str(fields[0]["id"])
        payload = {**APPLICANT, "responses": {field_id: "I am very motivated."}}
        resp = client.post(apply_url(job["public_id"]), json=payload)
        assert resp.status_code == 201

    def test_submit_with_radio_field(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        fields = client.put(
            f"{ADMIN_JOBS_URL}/{job['public_id']}/form-fields",
            json={"fields": [{"label": "Experience", "field_type": "radio",
                               "is_required": True,
                               "options": ["0-1 years", "2-5 years", "5+ years"]}]},
            headers=auth_headers,
        ).json()
        field_id = str(fields[0]["id"])
        payload = {**APPLICANT, "responses": {field_id: "2-5 years"}}
        resp = client.post(apply_url(job["public_id"]), json=payload)
        assert resp.status_code == 201

    def test_submit_with_checkbox_field(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        fields = client.put(
            f"{ADMIN_JOBS_URL}/{job['public_id']}/form-fields",
            json={"fields": [{"label": "Skills", "field_type": "checkbox",
                               "is_required": False,
                               "options": ["Python", "Go", "Rust"]}]},
            headers=auth_headers,
        ).json()
        field_id = str(fields[0]["id"])
        payload = {**APPLICANT, "responses": {field_id: ["Python", "Rust"]}}
        resp = client.post(apply_url(job["public_id"]), json=payload)
        assert resp.status_code == 201

    def test_optional_field_can_be_omitted(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        client.put(
            f"{ADMIN_JOBS_URL}/{job['public_id']}/form-fields",
            json={"fields": [{"label": "Portfolio URL", "field_type": "url",
                               "is_required": False, "options": []}]},
            headers=auth_headers,
        )
        resp = client.post(apply_url(job["public_id"]), json=APPLICANT)
        assert resp.status_code == 201

    def test_no_auth_required(self, client: TestClient, job: dict) -> None:
        resp = client.post(apply_url(job["public_id"]), json=APPLICANT)
        assert resp.status_code == 201


# ── Duplicate prevention ──────────────────────────────────────────────────────

class TestDuplicateApplication:
    def test_second_submission_same_email_returns_409(
        self, client: TestClient, job: dict
    ) -> None:
        client.post(apply_url(job["public_id"]), json=APPLICANT)
        resp = client.post(apply_url(job["public_id"]), json=APPLICANT)
        assert resp.status_code == 409

    def test_duplicate_check_is_case_insensitive(
        self, client: TestClient, job: dict
    ) -> None:
        client.post(apply_url(job["public_id"]), json=APPLICANT)
        payload = {**APPLICANT, "applicant_email": "JANE@EXAMPLE.COM"}
        resp = client.post(apply_url(job["public_id"]), json=payload)
        assert resp.status_code == 409

    def test_different_email_can_apply(self, client: TestClient, job: dict) -> None:
        client.post(apply_url(job["public_id"]), json=APPLICANT)
        payload = {**APPLICANT, "applicant_email": "other@example.com"}
        resp = client.post(apply_url(job["public_id"]), json=payload)
        assert resp.status_code == 201


# ── Job-state guards ──────────────────────────────────────────────────────────

class TestJobStateGuards:
    def test_inactive_job_returns_404(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        client.patch(f"{ADMIN_JOBS_URL}/{job['public_id']}/toggle", headers=auth_headers)
        resp = client.post(apply_url(job["public_id"]), json=APPLICANT)
        assert resp.status_code == 404

    def test_deleted_job_returns_404(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        client.delete(f"{ADMIN_JOBS_URL}/{job['public_id']}", headers=auth_headers)
        resp = client.post(apply_url(job["public_id"]), json=APPLICANT)
        assert resp.status_code == 404

    def test_expired_job_returns_404(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        resp = client.post(
            ADMIN_JOBS_URL,
            json={**BASE_JOB, "expires_at": past},
            headers=auth_headers,
        )
        expired_job = resp.json()
        resp = client.post(apply_url(expired_job["public_id"]), json=APPLICANT)
        assert resp.status_code == 404

    def test_unknown_job_returns_404(self, client: TestClient) -> None:
        resp = client.post(apply_url("no-such-id"), json=APPLICANT)
        assert resp.status_code == 404

    def test_external_url_job_returns_404(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        resp = client.post(
            ADMIN_JOBS_URL,
            json={
                **BASE_JOB,
                "application_mode": "external_url",
                "external_apply_url": "https://careers.example.com/apply",
            },
            headers=auth_headers,
        )
        ext_job = resp.json()
        resp = client.post(apply_url(ext_job["public_id"]), json=APPLICANT)
        assert resp.status_code == 404


# ── Applicant data validation ─────────────────────────────────────────────────

class TestApplicantDataValidation:
    def test_missing_name_returns_422(self, client: TestClient, job: dict) -> None:
        resp = client.post(
            apply_url(job["public_id"]),
            json={"applicant_email": "x@x.com", "responses": {}},
        )
        assert resp.status_code == 422

    def test_empty_name_returns_422(self, client: TestClient, job: dict) -> None:
        resp = client.post(
            apply_url(job["public_id"]),
            json={**APPLICANT, "applicant_name": ""},
        )
        assert resp.status_code == 422

    def test_invalid_email_returns_422(self, client: TestClient, job: dict) -> None:
        resp = client.post(
            apply_url(job["public_id"]),
            json={**APPLICANT, "applicant_email": "not-an-email"},
        )
        assert resp.status_code == 422

    def test_missing_email_returns_422(self, client: TestClient, job: dict) -> None:
        resp = client.post(
            apply_url(job["public_id"]),
            json={"applicant_name": "Jane", "responses": {}},
        )
        assert resp.status_code == 422


# ── Dynamic field response validation ────────────────────────────────────────

class TestFieldResponseValidation:
    def test_required_text_field_missing_returns_400(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        client.put(
            f"{ADMIN_JOBS_URL}/{job['public_id']}/form-fields",
            json={"fields": [{"label": "Why us?", "field_type": "text",
                               "is_required": True, "options": []}]},
            headers=auth_headers,
        )
        resp = client.post(apply_url(job["public_id"]), json=APPLICANT)
        assert resp.status_code == 400

    def test_required_text_field_blank_string_returns_400(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        fields = client.put(
            f"{ADMIN_JOBS_URL}/{job['public_id']}/form-fields",
            json={"fields": [{"label": "Why us?", "field_type": "text",
                               "is_required": True, "options": []}]},
            headers=auth_headers,
        ).json()
        field_id = str(fields[0]["id"])
        payload = {**APPLICANT, "responses": {field_id: "   "}}
        resp = client.post(apply_url(job["public_id"]), json=payload)
        assert resp.status_code == 400

    def test_radio_invalid_option_returns_400(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        fields = client.put(
            f"{ADMIN_JOBS_URL}/{job['public_id']}/form-fields",
            json={"fields": [{"label": "Level", "field_type": "radio",
                               "is_required": True,
                               "options": ["Junior", "Senior"]}]},
            headers=auth_headers,
        ).json()
        field_id = str(fields[0]["id"])
        payload = {**APPLICANT, "responses": {field_id: "Mid"}}
        resp = client.post(apply_url(job["public_id"]), json=payload)
        assert resp.status_code == 400

    def test_select_invalid_option_returns_400(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        fields = client.put(
            f"{ADMIN_JOBS_URL}/{job['public_id']}/form-fields",
            json={"fields": [{"label": "Team", "field_type": "select",
                               "is_required": True,
                               "options": ["Frontend", "Backend"]}]},
            headers=auth_headers,
        ).json()
        field_id = str(fields[0]["id"])
        payload = {**APPLICANT, "responses": {field_id: "DevOps"}}
        resp = client.post(apply_url(job["public_id"]), json=payload)
        assert resp.status_code == 400

    def test_checkbox_invalid_option_returns_400(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        fields = client.put(
            f"{ADMIN_JOBS_URL}/{job['public_id']}/form-fields",
            json={"fields": [{"label": "Tools", "field_type": "checkbox",
                               "is_required": True,
                               "options": ["Git", "Docker"]}]},
            headers=auth_headers,
        ).json()
        field_id = str(fields[0]["id"])
        payload = {**APPLICANT, "responses": {field_id: ["Git", "Kubernetes"]}}
        resp = client.post(apply_url(job["public_id"]), json=payload)
        assert resp.status_code == 400

    def test_email_field_invalid_value_returns_400(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        fields = client.put(
            f"{ADMIN_JOBS_URL}/{job['public_id']}/form-fields",
            json={"fields": [{"label": "LinkedIn email", "field_type": "email",
                               "is_required": True, "options": []}]},
            headers=auth_headers,
        ).json()
        field_id = str(fields[0]["id"])
        payload = {**APPLICANT, "responses": {field_id: "not-an-email"}}
        resp = client.post(apply_url(job["public_id"]), json=payload)
        assert resp.status_code == 400

    def test_url_field_invalid_value_returns_400(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        fields = client.put(
            f"{ADMIN_JOBS_URL}/{job['public_id']}/form-fields",
            json={"fields": [{"label": "Portfolio", "field_type": "url",
                               "is_required": True, "options": []}]},
            headers=auth_headers,
        ).json()
        field_id = str(fields[0]["id"])
        payload = {**APPLICANT, "responses": {field_id: "not-a-url"}}
        resp = client.post(apply_url(job["public_id"]), json=payload)
        assert resp.status_code == 400

    def test_url_field_valid_https_accepted(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        fields = client.put(
            f"{ADMIN_JOBS_URL}/{job['public_id']}/form-fields",
            json={"fields": [{"label": "Portfolio", "field_type": "url",
                               "is_required": True, "options": []}]},
            headers=auth_headers,
        ).json()
        field_id = str(fields[0]["id"])
        payload = {**APPLICANT, "responses": {field_id: "https://portfolio.dev"}}
        resp = client.post(apply_url(job["public_id"]), json=payload)
        assert resp.status_code == 201

    def test_number_field_non_numeric_returns_400(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        fields = client.put(
            f"{ADMIN_JOBS_URL}/{job['public_id']}/form-fields",
            json={"fields": [{"label": "Years exp.", "field_type": "number",
                               "is_required": True, "options": []}]},
            headers=auth_headers,
        ).json()
        field_id = str(fields[0]["id"])
        payload = {**APPLICANT, "responses": {field_id: "lots"}}
        resp = client.post(apply_url(job["public_id"]), json=payload)
        assert resp.status_code == 400

    def test_number_field_valid_numeric_string_accepted(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        fields = client.put(
            f"{ADMIN_JOBS_URL}/{job['public_id']}/form-fields",
            json={"fields": [{"label": "Years exp.", "field_type": "number",
                               "is_required": True, "options": []}]},
            headers=auth_headers,
        ).json()
        field_id = str(fields[0]["id"])
        payload = {**APPLICANT, "responses": {field_id: "4.5"}}
        resp = client.post(apply_url(job["public_id"]), json=payload)
        assert resp.status_code == 201

    def test_email_field_valid_email_accepted(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        fields = client.put(
            f"{ADMIN_JOBS_URL}/{job['public_id']}/form-fields",
            json={"fields": [{"label": "Alt email", "field_type": "email",
                               "is_required": True, "options": []}]},
            headers=auth_headers,
        ).json()
        field_id = str(fields[0]["id"])
        payload = {**APPLICANT, "responses": {field_id: "alt@example.com"}}
        resp = client.post(apply_url(job["public_id"]), json=payload)
        assert resp.status_code == 201
