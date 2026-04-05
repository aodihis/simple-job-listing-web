from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.form_field import FormFieldRead
from app.schemas.public_job import PublicJobListItem, PublicJobRead, PublicPaginatedJobs
from app.services import job_service

router = APIRouter(prefix="/api/v1/jobs", tags=["Public — Jobs"])


def _build_public_read(job) -> PublicJobRead:  # type: ignore[no-untyped-def]
    return PublicJobRead(
        public_id=job.public_id,
        title=job.title,
        description=job.description,
        employment_type=job.employment_type,
        location=job.location,
        is_remote=job.is_remote,
        application_mode=job.application_mode,
        external_apply_url=job.external_apply_url,
        tags=[{"name": t.name} for t in job.tags],
        form_fields=[
            FormFieldRead(
                id=f.id,
                label=f.label,
                field_type=f.field_type,
                is_required=f.is_required,
                options=f.options,
                order=f.order,
            )
            for f in sorted(job.form_fields, key=lambda f: f.order)
        ],
        created_at=job.created_at,
        expires_at=job.expires_at,
    )


@router.get(
    "",
    response_model=PublicPaginatedJobs,
    summary="List active job postings",
    description=(
        "Returns paginated active jobs visible to the public. "
        "Filters: full-text search (`q`), tags, employment_type, is_remote. "
        "Sort: `newest` (default) or `oldest`."
    ),
)
def list_public_jobs(
    q: str | None = Query(default=None, description="Search title and description."),
    tags: list[str] | None = Query(default=None, description="Filter by tag name (repeatable)."),
    employment_type: str | None = Query(
        default=None,
        description="Filter by employment type: full_time, part_time, contract, internship.",
    ),
    is_remote: bool | None = Query(default=None, description="Filter remote-friendly roles."),
    sort: str = Query(default="newest", description="Sort order: newest or oldest."),
    page: int = Query(default=1, ge=1, description="Page number."),
    per_page: int = Query(default=20, ge=1, le=100, description="Items per page."),
    db: Session = Depends(get_db),
) -> PublicPaginatedJobs:
    jobs, total = job_service.list_jobs_public(
        db,
        q=q,
        tags=tags,
        employment_type=employment_type,
        is_remote=is_remote,
        sort=sort,
        page=page,
        per_page=per_page,
    )
    return PublicPaginatedJobs(
        items=[
            PublicJobListItem(
                public_id=j.public_id,
                title=j.title,
                employment_type=j.employment_type,
                location=j.location,
                is_remote=j.is_remote,
                tags=[{"name": t.name} for t in j.tags],
                created_at=j.created_at,
                expires_at=j.expires_at,
            )
            for j in jobs
        ],
        total=total,
        page=page,
        per_page=per_page,
        pages=max(1, -(-total // per_page)),
    )


@router.get(
    "/{job_id}",
    response_model=PublicJobRead,
    summary="Get a single job posting",
    description="Returns full detail for an active, non-expired job. 404 if deleted, inactive, or expired.",
)
def get_public_job(
    job_id: str,
    db: Session = Depends(get_db),
) -> PublicJobRead:
    job = job_service.get_public_job(db, job_id)
    return _build_public_read(job)
