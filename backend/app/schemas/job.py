from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


class EmploymentType(str, Enum):
    full_time = "full_time"
    part_time = "part_time"
    contract = "contract"
    internship = "internship"


class ApplicationMode(str, Enum):
    form = "form"
    external_url = "external_url"


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255, description="Job title.")
    description: str = Field(min_length=1, description="Full job description. Markdown supported.")
    employment_type: EmploymentType = Field(description="Employment type.")
    location: str | None = Field(
        default=None, max_length=255, description="Office location. Omit or null for fully remote."
    )
    is_remote: bool = Field(default=False, description="Whether the role is remote.")
    application_mode: ApplicationMode = Field(
        default=ApplicationMode.form,
        description="'form' to use the built-in application form; 'external_url' to redirect applicants.",
    )
    external_apply_url: str | None = Field(
        default=None,
        max_length=500,
        description="Required when application_mode is 'external_url'.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="List of tag names (e.g. ['python', 'remote', 'senior']). Created automatically if new.",
    )
    expires_at: datetime | None = Field(
        default=None, description="Optional expiry date. Null = never expires."
    )

    @model_validator(mode="after")
    def validate_external_url_required(self) -> JobCreate:
        if self.application_mode == ApplicationMode.external_url and not self.external_apply_url:
            raise ValueError("external_apply_url is required when application_mode is 'external_url'.")
        return self

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, v: list[str]) -> list[str]:
        return [tag.strip().lower() for tag in v if tag.strip()]


class TagRead(BaseModel):
    name: str

    model_config = {"from_attributes": True}


class JobRead(BaseModel):
    public_id: str
    title: str
    description: str
    employment_type: str
    location: str | None
    is_remote: bool
    application_mode: str
    external_apply_url: str | None
    is_active: bool
    is_deleted: bool
    tags: list[TagRead]
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    posted_by_email: str = Field(description="Email of the admin who posted this job.")

    model_config = {"from_attributes": True}


class JobListItem(BaseModel):
    """Lightweight representation for list views."""

    public_id: str
    title: str
    employment_type: str
    location: str | None
    is_remote: bool
    is_active: bool
    is_deleted: bool
    tags: list[TagRead]
    created_at: datetime
    expires_at: datetime | None

    model_config = {"from_attributes": True}
