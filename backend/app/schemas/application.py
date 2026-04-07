from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_validator


class ApplicationStatus(str, Enum):
    new = "new"
    reviewed = "reviewed"
    rejected = "rejected"
    hired = "hired"


# ── Education / Experience sub-schemas ────────────────────────────────────────

class EducationEntry(BaseModel):
    institution: str = Field(description="School or university name.")
    degree: str = Field(description="Degree obtained, e.g. \"Bachelor's\", \"PhD\".")
    field_of_study: str | None = Field(default=None, description="Major or field of study.")
    gpa: str | None = Field(default=None, description="GPA, e.g. \"3.8\" or \"3.8/4.0\".")
    start_year: int | None = Field(default=None, description="Year studies began.")
    end_year: int | None = Field(default=None, description="Year studies ended; null means currently enrolled.")


class ExperienceEntry(BaseModel):
    title: str = Field(description="Job title.")
    company: str = Field(description="Employer name.")
    summary: str | None = Field(default=None, description="Brief description of responsibilities and achievements.")
    start_year: int | None = Field(default=None, description="Year the role started.")
    end_year: int | None = Field(default=None, description="Year the role ended; null means current position.")


# ── Write schema (submitted by applicant) ─────────────────────────────────────

class ApplicationCreate(BaseModel):
    applicant_name: str = Field(min_length=1, max_length=200, description="Full name of the applicant.")
    applicant_email: EmailStr = Field(description="Applicant's email address.")
    responses: dict[str, str | list[str]] = Field(
        default_factory=dict,
        description=(
            "Answers to the job's custom form fields. "
            "Keys are string form-field IDs; values are the applicant's answers. "
            "Single-choice fields (text, email, url, number, radio, select) use a string value. "
            "Multi-choice fields (checkbox) use a list of strings."
        ),
    )
    education: list[EducationEntry] = Field(
        default_factory=list,
        description="List of education entries (optional).",
    )
    experience: list[ExperienceEntry] = Field(
        default_factory=list,
        description="List of work experience entries (optional).",
    )

    @field_validator("applicant_name", mode="before")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


# ── Read schemas ──────────────────────────────────────────────────────────────

class ApplicationConfirmation(BaseModel):
    """Minimal response returned to the applicant after successful submission."""
    public_id: str
    message: str = "Your application has been submitted successfully."


class ApplicationRead(BaseModel):
    """Full application detail — used in the admin dashboard."""
    public_id: str
    applicant_name: str
    applicant_email: str
    responses: dict[str, str | list[str]]
    status: str
    created_at: datetime
    job_public_id: str
    job_title: str
    cv_filename: str | None = None
    education: list[EducationEntry] = []
    experience: list[ExperienceEntry] = []

    model_config = {"from_attributes": True}
