from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.form_field import FormFieldRead


class PublicTagRead(BaseModel):
    name: str

    model_config = {"from_attributes": True}


class PublicJobListItem(BaseModel):
    """Lightweight job representation for public listing — no admin-only fields."""

    public_id: str
    title: str
    employment_type: str
    location: str | None
    is_remote: bool
    salary_min: int | None
    salary_max: int | None
    tags: list[PublicTagRead]
    created_at: datetime
    expires_at: datetime | None

    model_config = {"from_attributes": True}


class PublicJobRead(BaseModel):
    """Full job detail for public view — no admin-only fields."""

    public_id: str
    title: str
    description: str
    employment_type: str
    location: str | None
    is_remote: bool
    salary_min: int | None
    salary_max: int | None
    application_mode: str
    external_apply_url: str | None
    tags: list[PublicTagRead]
    form_fields: list[FormFieldRead] = Field(
        default_factory=list,
        description="Custom application form fields. Populated when application_mode is 'form'.",
    )
    created_at: datetime
    expires_at: datetime | None

    model_config = {"from_attributes": True}


class PublicPaginatedJobs(BaseModel):
    items: list[PublicJobListItem]
    total: int
    page: int
    per_page: int
    pages: int
