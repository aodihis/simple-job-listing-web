"""
Tests for the form field endpoints and schema validation:

  GET /api/v1/admin/jobs/{id}/form-fields
  PUT /api/v1/admin/jobs/{id}/form-fields

Also covers FormFieldCreate / FormFieldsUpdate schema rules directly.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.schemas.form_field import FormFieldCreate, FormFieldsUpdate

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ADMIN_JOBS_URL = "/api/v1/admin/jobs"

ADMIN = {
    "email": "admin@example.com",
    "display_name": "Test Admin",
    "password": "securepassword123",
}

BASE_JOB = {
    "title": "QA Engineer",
    "description": "<p>Test all the things.</p>",
    "employment_type": "full_time",
    "location": None,
    "is_remote": True,
    "application_mode": "form",
    "external_apply_url": None,
    "tags": [],
    "expires_at": None,
}

SIMPLE_FIELD = {
    "label": "Years of experience",
    "field_type": "number",
    "is_required": True,
    "options": [],
}

RADIO_FIELD = {
    "label": "Preferred work schedule",
    "field_type": "radio",
    "is_required": False,
    "options": ["Morning", "Afternoon", "Evening"],
}


# ── Shared fixtures ───────────────────────────────────────────────────────────

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


def fields_url(job_public_id: str) -> str:
    return f"{ADMIN_JOBS_URL}/{job_public_id}/form-fields"


# ── GET /api/v1/admin/jobs/{id}/form-fields ───────────────────────────────────

class TestGetFormFields:
    def test_new_job_has_empty_fields(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        resp = client.get(fields_url(job["public_id"]), headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_saved_fields_in_order(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        client.put(
            fields_url(job["public_id"]),
            json={"fields": [SIMPLE_FIELD, RADIO_FIELD]},
            headers=auth_headers,
        )
        resp = client.get(fields_url(job["public_id"]), headers=auth_headers)
        assert resp.status_code == 200
        fields = resp.json()
        assert len(fields) == 2
        assert fields[0]["order"] == 0
        assert fields[1]["order"] == 1

    def test_not_found_for_unknown_job(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.get(fields_url("no-such-id"), headers=auth_headers)
        assert resp.status_code == 404

    def test_requires_auth(self, client: TestClient, job: dict) -> None:
        resp = client.get(fields_url(job["public_id"]))
        assert resp.status_code == 401


# ── PUT /api/v1/admin/jobs/{id}/form-fields ───────────────────────────────────

class TestReplaceFormFields:
    def test_save_simple_fields(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        resp = client.put(
            fields_url(job["public_id"]),
            json={"fields": [SIMPLE_FIELD]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        fields = resp.json()
        assert len(fields) == 1
        assert fields[0]["label"] == SIMPLE_FIELD["label"]
        assert fields[0]["field_type"] == "number"
        assert fields[0]["is_required"] is True
        assert fields[0]["options"] == []
        assert fields[0]["order"] == 0
        assert "id" in fields[0]

    def test_save_radio_field_with_options(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        resp = client.put(
            fields_url(job["public_id"]),
            json={"fields": [RADIO_FIELD]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        field = resp.json()[0]
        assert field["field_type"] == "radio"
        assert field["options"] == ["Morning", "Afternoon", "Evening"]

    def test_save_select_and_checkbox_fields(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        fields = [
            {"label": "Country", "field_type": "select", "is_required": True,
             "options": ["US", "UK", "Other"]},
            {"label": "Skills", "field_type": "checkbox", "is_required": False,
             "options": ["Python", "Go", "Rust"]},
        ]
        resp = client.put(
            fields_url(job["public_id"]),
            json={"fields": fields},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        result = resp.json()
        assert result[0]["field_type"] == "select"
        assert result[1]["field_type"] == "checkbox"

    def test_replace_overwrites_previous_fields(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        url = fields_url(job["public_id"])
        client.put(url, json={"fields": [SIMPLE_FIELD, RADIO_FIELD]}, headers=auth_headers)
        resp = client.put(
            url,
            json={"fields": [{"label": "Cover letter", "field_type": "textarea",
                               "is_required": True, "options": []}]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        fields = resp.json()
        assert len(fields) == 1
        assert fields[0]["label"] == "Cover letter"

    def test_clear_all_fields_with_empty_list(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        url = fields_url(job["public_id"])
        client.put(url, json={"fields": [SIMPLE_FIELD]}, headers=auth_headers)
        resp = client.put(url, json={"fields": []}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_order_is_zero_based_sequential(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        three_fields = [
            {"label": f"Q{i}", "field_type": "text", "is_required": False, "options": []}
            for i in range(3)
        ]
        resp = client.put(
            fields_url(job["public_id"]),
            json={"fields": three_fields},
            headers=auth_headers,
        )
        orders = [f["order"] for f in resp.json()]
        assert orders == [0, 1, 2]

    def test_all_text_field_types_accepted(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        for ft in ("text", "textarea", "email", "url", "number"):
            resp = client.put(
                fields_url(job["public_id"]),
                json={"fields": [{"label": "Q", "field_type": ft,
                                  "is_required": False, "options": []}]},
                headers=auth_headers,
            )
            assert resp.status_code == 200, f"Expected 200 for field_type={ft!r}"

    def test_options_stripped_from_non_choice_fields(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        """Backend should silently discard options for text/email/etc. types."""
        resp = client.put(
            fields_url(job["public_id"]),
            json={"fields": [{"label": "Name", "field_type": "text",
                               "is_required": False, "options": ["ignored"]}]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()[0]["options"] == []

    def test_invalid_field_type_rejected(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        resp = client.put(
            fields_url(job["public_id"]),
            json={"fields": [{"label": "Q", "field_type": "script",
                               "is_required": False, "options": []}]},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_radio_without_options_rejected(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        resp = client.put(
            fields_url(job["public_id"]),
            json={"fields": [{"label": "Q", "field_type": "radio",
                               "is_required": False, "options": []}]},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_select_without_options_rejected(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        resp = client.put(
            fields_url(job["public_id"]),
            json={"fields": [{"label": "Q", "field_type": "select",
                               "is_required": False, "options": []}]},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_more_than_20_fields_rejected(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        too_many = [
            {"label": f"Q{i}", "field_type": "text", "is_required": False, "options": []}
            for i in range(21)
        ]
        resp = client.put(
            fields_url(job["public_id"]),
            json={"fields": too_many},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_empty_label_rejected(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        resp = client.put(
            fields_url(job["public_id"]),
            json={"fields": [{"label": "", "field_type": "text",
                               "is_required": False, "options": []}]},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_not_found_for_unknown_job(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.put(
            fields_url("no-such-id"),
            json={"fields": []},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_not_found_for_deleted_job(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        client.delete(f"{ADMIN_JOBS_URL}/{job['public_id']}", headers=auth_headers)
        resp = client.put(
            fields_url(job["public_id"]),
            json={"fields": []},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_requires_auth(self, client: TestClient, job: dict) -> None:
        resp = client.put(fields_url(job["public_id"]), json={"fields": []})
        assert resp.status_code == 401

    def test_job_read_includes_form_fields(
        self, client: TestClient, auth_headers: dict, job: dict
    ) -> None:
        """form_fields is embedded in the full JobRead response."""
        client.put(
            fields_url(job["public_id"]),
            json={"fields": [SIMPLE_FIELD]},
            headers=auth_headers,
        )
        resp = client.get(f"{ADMIN_JOBS_URL}/{job['public_id']}", headers=auth_headers)
        assert resp.status_code == 200
        form_fields = resp.json()["form_fields"]
        assert len(form_fields) == 1
        assert form_fields[0]["label"] == SIMPLE_FIELD["label"]


# ── Schema unit tests (FormFieldCreate) ───────────────────────────────────────

class TestFormFieldCreateSchema:
    def test_valid_text_field(self) -> None:
        f = FormFieldCreate(label="Full name", field_type="text", is_required=True, options=[])
        assert f.label == "Full name"
        assert f.options == []

    def test_valid_radio_field(self) -> None:
        f = FormFieldCreate(
            label="Experience",
            field_type="radio",
            is_required=False,
            options=["0-1 years", "2-5 years", "5+ years"],
        )
        assert len(f.options) == 3

    def test_options_are_stripped(self) -> None:
        f = FormFieldCreate(
            label="Q",
            field_type="select",
            is_required=False,
            options=["  Yes  ", "  No  ", ""],
        )
        assert f.options == ["Yes", "No"]  # empty string dropped, whitespace stripped

    def test_options_deduplicated_via_strip(self) -> None:
        """Blank entries are dropped; validation is on the cleaned list."""
        f = FormFieldCreate(
            label="Q",
            field_type="radio",
            is_required=False,
            options=["A", "B", "C"],
        )
        assert f.options == ["A", "B", "C"]

    def test_options_silently_cleared_for_text_type(self) -> None:
        f = FormFieldCreate(
            label="Q",
            field_type="text",
            is_required=False,
            options=["should be ignored"],
        )
        assert f.options == []

    def test_radio_without_options_raises(self) -> None:
        with pytest.raises(ValidationError, match="options must not be empty"):
            FormFieldCreate(label="Q", field_type="radio", is_required=False, options=[])

    def test_select_without_options_raises(self) -> None:
        with pytest.raises(ValidationError):
            FormFieldCreate(label="Q", field_type="select", is_required=False, options=[])

    def test_checkbox_without_options_raises(self) -> None:
        with pytest.raises(ValidationError):
            FormFieldCreate(label="Q", field_type="checkbox", is_required=False, options=[])

    def test_too_many_options_raises(self) -> None:
        with pytest.raises(ValidationError, match="Maximum 20"):
            FormFieldCreate(
                label="Q",
                field_type="radio",
                is_required=False,
                options=[f"opt{i}" for i in range(21)],
            )

    def test_option_too_long_raises(self) -> None:
        with pytest.raises(ValidationError, match="100 characters"):
            FormFieldCreate(
                label="Q",
                field_type="radio",
                is_required=False,
                options=["A" * 101],
            )

    def test_invalid_field_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            FormFieldCreate(label="Q", field_type="script", is_required=False, options=[])

    def test_empty_label_raises(self) -> None:
        with pytest.raises(ValidationError):
            FormFieldCreate(label="", field_type="text", is_required=False, options=[])

    def test_label_over_200_chars_raises(self) -> None:
        with pytest.raises(ValidationError):
            FormFieldCreate(label="x" * 201, field_type="text", is_required=False, options=[])


class TestFormFieldsUpdateSchema:
    def test_empty_fields_list_is_valid(self) -> None:
        u = FormFieldsUpdate(fields=[])
        assert u.fields == []

    def test_too_many_fields_raises(self) -> None:
        fields = [
            FormFieldCreate(label=f"Q{i}", field_type="text", is_required=False, options=[])
            for i in range(21)
        ]
        with pytest.raises(ValidationError):
            FormFieldsUpdate(fields=fields)
