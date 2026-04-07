from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.application import ApplicationConfirmation, ApplicationCreate
from app.schemas.form_field import FormFieldRead
from app.schemas.public_job import PublicJobListItem, PublicJobRead, PublicPaginatedJobs
from app.services import application_service, email_service, job_service
from app.utils.exceptions import BadRequestError

router = APIRouter(prefix="/api/v1/jobs", tags=["Public — Jobs"])


def _build_public_read(job) -> PublicJobRead:  # type: ignore[no-untyped-def]
    return PublicJobRead(
        public_id=job.public_id,
        title=job.title,
        description=job.description,
        employment_type=job.employment_type,
        location=job.location,
        is_remote=job.is_remote,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
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
                salary_min=j.salary_min,
                salary_max=j.salary_max,
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


@router.post(
    "/{job_id}/apply",
    response_model=ApplicationConfirmation,
    status_code=201,
    summary="Submit a job application",
    description=(
        "Submit an application for a job that uses the built-in form (`application_mode='form'`). "
        "Accepts multipart/form-data with applicant details, optional form responses (JSON string), "
        "and a required CV file (PDF, DOC, or DOCX, max 10 MB). "
        "One submission per email address per job. "
        "Returns 404 for jobs using an external URL or that are inactive/expired/deleted. "
        "Returns 409 if the same email has already applied."
    ),
)
def apply_for_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    applicant_name: str = Form(..., min_length=1, max_length=200, description="Full name of the applicant."),
    applicant_email: str = Form(..., description="Applicant's email address."),
    responses_json: str = Form(
        default="{}",
        description=(
            "JSON-encoded dict mapping form field IDs (as strings) to answers. "
            "Single-choice fields use a string value; checkbox fields use a JSON array."
        ),
    ),
    education_json: str = Form(
        default="[]",
        description="JSON-encoded array of education entries.",
    ),
    experience_json: str = Form(
        default="[]",
        description="JSON-encoded array of work experience entries.",
    ),
    cv_file: UploadFile = File(..., description="CV/resume file. Must be PDF, DOC, or DOCX. Max 10 MB."),
    db: Session = Depends(get_db),
) -> ApplicationConfirmation:
    try:
        responses: dict[str, str | list[str]] = json.loads(responses_json)
    except json.JSONDecodeError:
        raise BadRequestError("responses_json must be a valid JSON object.")

    try:
        education_raw = json.loads(education_json)
        experience_raw = json.loads(experience_json)
    except json.JSONDecodeError:
        raise BadRequestError("education_json and experience_json must be valid JSON arrays.")

    data = ApplicationCreate(
        applicant_name=applicant_name,
        applicant_email=applicant_email,
        responses=responses,
        education=education_raw,
        experience=experience_raw,
    )

    cv_content = cv_file.file.read()

    result = application_service.submit_application(
        db,
        job_id,
        data,
        cv_filename=cv_file.filename or "cv",
        cv_content=cv_content,
        cv_content_type=cv_file.content_type or "",
    )
    background_tasks.add_task(
        email_service.send_new_application_notification,
        application_public_id=result.public_id,
    )
    background_tasks.add_task(
        email_service.send_application_confirmation,
        application_public_id=result.public_id,
    )
    return result
