"""
Tests for POST /api/v1/jobs/{id}/apply — public application submission.
Covers happy path, field validation, duplicate prevention, and job-state guards.

The apply endpoint now accepts multipart/form-data:
  - applicant_name  (form field)
  - applicant_email (form field)
  - responses_json  (form field, JSON-encoded dict, default "{}")
  - cv_file         (file upload, required, PDF/DOC/DOCX ≤ 10 MB)
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from io import BytesIO

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

# Minimal valid PDF bytes (not a real PDF but accepted by content-type)
_FAKE_PDF = b"%PDF-1.4 fake"
_FAKE_DOCX = b"PK fake docx"


def _apply(
    client: TestClient,
    job_public_id: str,
    *,
    name: str = "Jane Doe",
    email: str = "jane@example.com",
    responses: dict | None = None,
    cv_bytes: bytes = _FAKE_PDF,
    cv_filename: str = "cv.pdf",
    cv_content_type: str = "application/pdf",
) -> "Response":  # type: ignore[name-defined]
    """Helper: POST a multipart application."""
    data = {
        "applicant_name": name,
        "applicant_email": email,
        "responses_json": json.dumps(responses or {}),
    }
    files = {"cv_file": (cv_filename, BytesIO(cv_bytes), cv_content_type)}
    return client.post(f"/api/v1/jobs/{job_public_id}/apply", data=data, files=files)


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


def set_form_fields(client: TestClient, headers: dict, job_id: str, fields: list) -> list:
    resp = client.put(
        f"{ADMIN_JOBS_URL}/{job_id}/form-fields",
        json={"fields": fields},
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


# ── Happy path ────────────────────────────────────────────────────────────────

class TestSubmitApplication:
    def test_submit_with_no_form_fields_returns_201(
        self, client: TestClient, job: dict
    ) -> None:
        resp = _apply(client, job["public_id"])
        assert resp.status_code == 201
        body = resp.json()
        assert "public_id" in body
        assert "message" in body

    def test_submit_stores_lowercase_email(
        self, client: TestClient, job: dict
    ) -> None:
        resp = _apply(client, job["public_id"], email="Jane@Example.COM")
        assert resp.status_code == 201

    def test_submit_with_text_field(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        fields = set_form_fields(
            client, auth_headers, job["public_id"],
            [{"label": "Cover letter", "field_type": "textarea", "is_required": True, "options": []}],
        )
        field_id = str(fields[0]["id"])
        resp = _apply(client, job["public_id"], responses={field_id: "I am very motivated."})
        assert resp.status_code == 201

    def test_submit_with_radio_field(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        fields = set_form_fields(
            client, auth_headers, job["public_id"],
            [{"label": "Experience", "field_type": "radio", "is_required": True,
              "options": ["0-1 years", "2-5 years", "5+ years"]}],
        )
        field_id = str(fields[0]["id"])
        resp = _apply(client, job["public_id"], responses={field_id: "2-5 years"})
        assert resp.status_code == 201

    def test_submit_with_checkbox_field(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        fields = set_form_fields(
            client, auth_headers, job["public_id"],
            [{"label": "Skills", "field_type": "checkbox", "is_required": False,
              "options": ["Python", "Go", "Rust"]}],
        )
        field_id = str(fields[0]["id"])
        resp = _apply(client, job["public_id"], responses={field_id: ["Python", "Rust"]})
        assert resp.status_code == 201

    def test_optional_field_can_be_omitted(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        set_form_fields(
            client, auth_headers, job["public_id"],
            [{"label": "Portfolio URL", "field_type": "url", "is_required": False, "options": []}],
        )
        resp = _apply(client, job["public_id"])
        assert resp.status_code == 201

    def test_no_auth_required(self, client: TestClient, job: dict) -> None:
        resp = _apply(client, job["public_id"])
        assert resp.status_code == 201

    def test_docx_cv_accepted(self, client: TestClient, job: dict) -> None:
        resp = _apply(
            client, job["public_id"],
            cv_bytes=_FAKE_DOCX,
            cv_filename="cv.docx",
            cv_content_type=(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
        )
        assert resp.status_code == 201


# ── CV validation ─────────────────────────────────────────────────────────────

class TestCvValidation:
    def test_missing_cv_returns_422(self, client: TestClient, job: dict) -> None:
        """Endpoint requires cv_file — omitting it yields 422."""
        data = {"applicant_name": "Jane", "applicant_email": "jane@example.com", "responses_json": "{}"}
        resp = client.post(apply_url(job["public_id"]), data=data)
        assert resp.status_code == 422

    def test_empty_cv_returns_400(self, client: TestClient, job: dict) -> None:
        resp = _apply(client, job["public_id"], cv_bytes=b"", cv_filename="cv.pdf")
        assert resp.status_code == 400

    def test_oversized_cv_returns_400(self, client: TestClient, job: dict) -> None:
        big = b"x" * (10 * 1024 * 1024 + 1)
        resp = _apply(client, job["public_id"], cv_bytes=big)
        assert resp.status_code == 400

    def test_invalid_extension_and_content_type_returns_400(
        self, client: TestClient, job: dict
    ) -> None:
        resp = _apply(
            client, job["public_id"],
            cv_bytes=b"plain text",
            cv_filename="cv.txt",
            cv_content_type="text/plain",
        )
        assert resp.status_code == 400


# ── Duplicate prevention ──────────────────────────────────────────────────────

class TestDuplicateApplication:
    def test_second_submission_same_email_returns_409(
        self, client: TestClient, job: dict
    ) -> None:
        _apply(client, job["public_id"])
        resp = _apply(client, job["public_id"])
        assert resp.status_code == 409

    def test_duplicate_check_is_case_insensitive(
        self, client: TestClient, job: dict
    ) -> None:
        _apply(client, job["public_id"], email="jane@example.com")
        resp = _apply(client, job["public_id"], email="JANE@EXAMPLE.COM")
        assert resp.status_code == 409

    def test_different_email_can_apply(self, client: TestClient, job: dict) -> None:
        _apply(client, job["public_id"], email="jane@example.com")
        resp = _apply(client, job["public_id"], email="other@example.com")
        assert resp.status_code == 201


# ── Job-state guards ──────────────────────────────────────────────────────────

class TestJobStateGuards:
    def test_inactive_job_returns_404(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        client.patch(f"{ADMIN_JOBS_URL}/{job['public_id']}/toggle", headers=auth_headers)
        resp = _apply(client, job["public_id"])
        assert resp.status_code == 404

    def test_deleted_job_returns_404(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        client.delete(f"{ADMIN_JOBS_URL}/{job['public_id']}", headers=auth_headers)
        resp = _apply(client, job["public_id"])
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
        resp = _apply(client, expired_job["public_id"])
        assert resp.status_code == 404

    def test_unknown_job_returns_404(self, client: TestClient) -> None:
        resp = _apply(client, "no-such-id")
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
        resp = _apply(client, ext_job["public_id"])
        assert resp.status_code == 404


# ── Applicant data validation ─────────────────────────────────────────────────

class TestApplicantDataValidation:
    def test_missing_name_returns_422(self, client: TestClient, job: dict) -> None:
        data = {"applicant_email": "x@x.com", "responses_json": "{}"}
        files = {"cv_file": ("cv.pdf", BytesIO(_FAKE_PDF), "application/pdf")}
        resp = client.post(apply_url(job["public_id"]), data=data, files=files)
        assert resp.status_code == 422

    def test_empty_name_returns_422(self, client: TestClient, job: dict) -> None:
        resp = _apply(client, job["public_id"], name="")
        assert resp.status_code == 422

    def test_invalid_email_returns_422(self, client: TestClient, job: dict) -> None:
        resp = _apply(client, job["public_id"], email="not-an-email")
        assert resp.status_code == 422

    def test_missing_email_returns_422(self, client: TestClient, job: dict) -> None:
        data = {"applicant_name": "Jane", "responses_json": "{}"}
        files = {"cv_file": ("cv.pdf", BytesIO(_FAKE_PDF), "application/pdf")}
        resp = client.post(apply_url(job["public_id"]), data=data, files=files)
        assert resp.status_code == 422


# ── Dynamic field response validation ────────────────────────────────────────

class TestFieldResponseValidation:
    def test_required_text_field_missing_returns_400(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        set_form_fields(
            client, auth_headers, job["public_id"],
            [{"label": "Why us?", "field_type": "text", "is_required": True, "options": []}],
        )
        resp = _apply(client, job["public_id"])
        assert resp.status_code == 400

    def test_required_text_field_blank_string_returns_400(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        fields = set_form_fields(
            client, auth_headers, job["public_id"],
            [{"label": "Why us?", "field_type": "text", "is_required": True, "options": []}],
        )
        field_id = str(fields[0]["id"])
        resp = _apply(client, job["public_id"], responses={field_id: "   "})
        assert resp.status_code == 400

    def test_radio_invalid_option_returns_400(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        fields = set_form_fields(
            client, auth_headers, job["public_id"],
            [{"label": "Level", "field_type": "radio", "is_required": True,
              "options": ["Junior", "Senior"]}],
        )
        field_id = str(fields[0]["id"])
        resp = _apply(client, job["public_id"], responses={field_id: "Mid"})
        assert resp.status_code == 400

    def test_select_invalid_option_returns_400(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        fields = set_form_fields(
            client, auth_headers, job["public_id"],
            [{"label": "Team", "field_type": "select", "is_required": True,
              "options": ["Frontend", "Backend"]}],
        )
        field_id = str(fields[0]["id"])
        resp = _apply(client, job["public_id"], responses={field_id: "DevOps"})
        assert resp.status_code == 400

    def test_checkbox_invalid_option_returns_400(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        fields = set_form_fields(
            client, auth_headers, job["public_id"],
            [{"label": "Tools", "field_type": "checkbox", "is_required": True,
              "options": ["Git", "Docker"]}],
        )
        field_id = str(fields[0]["id"])
        resp = _apply(client, job["public_id"], responses={field_id: ["Git", "Kubernetes"]})
        assert resp.status_code == 400

    def test_email_field_invalid_value_returns_400(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        fields = set_form_fields(
            client, auth_headers, job["public_id"],
            [{"label": "LinkedIn email", "field_type": "email", "is_required": True, "options": []}],
        )
        field_id = str(fields[0]["id"])
        resp = _apply(client, job["public_id"], responses={field_id: "not-an-email"})
        assert resp.status_code == 400

    def test_url_field_invalid_value_returns_400(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        fields = set_form_fields(
            client, auth_headers, job["public_id"],
            [{"label": "Portfolio", "field_type": "url", "is_required": True, "options": []}],
        )
        field_id = str(fields[0]["id"])
        resp = _apply(client, job["public_id"], responses={field_id: "not-a-url"})
        assert resp.status_code == 400

    def test_url_field_valid_https_accepted(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        fields = set_form_fields(
            client, auth_headers, job["public_id"],
            [{"label": "Portfolio", "field_type": "url", "is_required": True, "options": []}],
        )
        field_id = str(fields[0]["id"])
        resp = _apply(client, job["public_id"], responses={field_id: "https://portfolio.dev"})
        assert resp.status_code == 201

    def test_number_field_non_numeric_returns_400(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        fields = set_form_fields(
            client, auth_headers, job["public_id"],
            [{"label": "Years exp.", "field_type": "number", "is_required": True, "options": []}],
        )
        field_id = str(fields[0]["id"])
        resp = _apply(client, job["public_id"], responses={field_id: "lots"})
        assert resp.status_code == 400

    def test_number_field_valid_numeric_string_accepted(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        fields = set_form_fields(
            client, auth_headers, job["public_id"],
            [{"label": "Years exp.", "field_type": "number", "is_required": True, "options": []}],
        )
        field_id = str(fields[0]["id"])
        resp = _apply(client, job["public_id"], responses={field_id: "4.5"})
        assert resp.status_code == 201

    def test_email_field_valid_email_accepted(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        fields = set_form_fields(
            client, auth_headers, job["public_id"],
            [{"label": "Alt email", "field_type": "email", "is_required": True, "options": []}],
        )
        field_id = str(fields[0]["id"])
        resp = _apply(client, job["public_id"], responses={field_id: "alt@example.com"})
        assert resp.status_code == 201
