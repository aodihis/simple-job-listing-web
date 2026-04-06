from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_active_admin
from app.models.user import AdminUser
from app.schemas.form_field import FormFieldRead, FormFieldsUpdate
from app.schemas.job import JobCreate, JobListItem, JobRead
from app.services import form_field_service, job_service

router = APIRouter(prefix="/api/v1/admin/jobs", tags=["Admin — Jobs"])


def _build_job_read(job) -> JobRead:  # type: ignore[no-untyped-def]
    return JobRead(
        public_id=job.public_id,
        title=job.title,
        description=job.description,
        employment_type=job.employment_type,
        location=job.location,
        is_remote=job.is_remote,
        application_mode=job.application_mode,
        external_apply_url=job.external_apply_url,
        is_active=job.is_active,
        is_deleted=job.is_deleted,
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
        expires_at=job.expires_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
        posted_by_email=job.posted_by.email,
    )


@router.post(
    "",
    response_model=JobRead,
    status_code=201,
    summary="Create a new job posting",
    description="Create a job. Tags are created automatically if they don't exist yet.",
)
def create_job(
    body: JobCreate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_active_admin),
) -> JobRead:
    job = job_service.create_job(db, body, current_user)
    return _build_job_read(job)


@router.get(
    "",
    response_model=dict,
    summary="List all jobs (admin)",
    description="Returns paginated job list including inactive jobs. Soft-deleted jobs excluded by default.",
)
def list_jobs(
    page: int = Query(default=1, ge=1, description="Page number."),
    per_page: int = Query(default=20, ge=1, le=100, description="Items per page."),
    include_deleted: bool = Query(default=False, description="Include soft-deleted jobs."),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_active_admin),
) -> dict:
    jobs, total = job_service.list_jobs_admin(
        db, include_deleted=include_deleted, page=page, per_page=per_page
    )
    return {
        "items": [
            JobListItem(
                public_id=j.public_id,
                title=j.title,
                employment_type=j.employment_type,
                location=j.location,
                is_remote=j.is_remote,
                is_active=j.is_active,
                is_deleted=j.is_deleted,
                tags=[{"name": t.name} for t in j.tags],
                created_at=j.created_at,
                expires_at=j.expires_at,
            )
            for j in jobs
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, -(-total // per_page)),  # ceiling division
    }


@router.get(
    "/{job_id}",
    response_model=JobRead,
    summary="Get a single job (admin)",
    description="Returns full job detail including description.",
)
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_active_admin),
) -> JobRead:
    job = job_service.get_job_by_public_id(db, job_id)
    return _build_job_read(job)


@router.patch(
    "/{job_id}/toggle",
    response_model=JobRead,
    summary="Toggle job active state",
    description="Flips `is_active` on a job. Soft-deleted jobs cannot be toggled.",
)
def toggle_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_active_admin),
) -> JobRead:
    job = job_service.toggle_job_active(db, job_id, current_user)
    return _build_job_read(job)


@router.delete(
    "/{job_id}",
    response_model=JobRead,
    summary="Soft-delete a job",
    description="Sets `is_deleted=True` and `is_active=False`. Cannot be undone via the API.",
)
def delete_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_active_admin),
) -> JobRead:
    job = job_service.delete_job(db, job_id, current_user)
    return _build_job_read(job)


@router.get(
    "/{job_id}/form-fields",
    response_model=list[FormFieldRead],
    summary="Get application form fields for a job",
    description="Returns the ordered list of custom fields for the job's built-in application form.",
)
def get_form_fields(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_active_admin),
) -> list[FormFieldRead]:
    return form_field_service.get_form_fields(db, job_id)


@router.put(
    "/{job_id}/form-fields",
    response_model=list[FormFieldRead],
    summary="Replace application form fields for a job",
    description=(
        "Atomically replaces all custom form fields for the job's built-in application form. "
        "Send an empty `fields` array to clear all fields. "
        "Maximum 20 fields. Allowed types: text, textarea, email, url, number, radio, select, checkbox. "
        "radio / select / checkbox require a non-empty `options` list (max 20 items, each ≤ 100 chars)."
    ),
)
def replace_form_fields(
    job_id: str,
    body: FormFieldsUpdate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_active_admin),
) -> list[FormFieldRead]:
    return form_field_service.replace_form_fields(db, job_id, body, current_user)
