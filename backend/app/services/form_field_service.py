from __future__ import annotations

from sqlalchemy.orm import Session

from app.logging.config import get_logger
from app.models.form_field import JobFormField
from app.models.job import Job
from app.models.user import AdminUser
from app.schemas.form_field import FormFieldRead, FormFieldsUpdate
from app.utils.exceptions import ForbiddenError, NotFoundError

log = get_logger(__name__)


def _get_editable_job(db: Session, job_id: str, current_user: AdminUser) -> Job:
    """Return a job that exists and is not soft-deleted. Raises NotFoundError otherwise."""
    job: Job | None = db.query(Job).filter(Job.public_id == job_id).first()
    if job is None or job.is_deleted:
        raise NotFoundError(f"Job '{job_id}' not found.")
    return job


def get_form_fields(db: Session, job_id: str) -> list[FormFieldRead]:
    """
    Return all form fields for a job ordered by their display order.

    Public-safe — does not require auth; the caller is responsible for
    ensuring the job is visible before exposing these fields publicly.
    """
    job: Job | None = db.query(Job).filter(Job.public_id == job_id).first()
    if job is None or job.is_deleted:
        raise NotFoundError(f"Job '{job_id}' not found.")
    return [_to_read(f) for f in sorted(job.form_fields, key=lambda f: f.order)]


def replace_form_fields(
    db: Session,
    job_id: str,
    payload: FormFieldsUpdate,
    current_user: AdminUser,
) -> list[FormFieldRead]:
    """
    Atomically replace all form fields for a job.

    Strategy: delete existing rows for this job, insert the new list in order.
    This keeps the implementation simple and avoids partial-update drift.
    """
    job = _get_editable_job(db, job_id, current_user)

    # Delete all existing fields for this job
    db.query(JobFormField).filter(JobFormField.job_id == job.id).delete()

    new_fields: list[JobFormField] = []
    for idx, field_data in enumerate(payload.fields):
        ff = JobFormField(
            job_id=job.id,
            order=idx,
            label=field_data.label,
            field_type=field_data.field_type.value,
            is_required=field_data.is_required,
        )
        ff.options = field_data.options
        db.add(ff)
        new_fields.append(ff)

    db.flush()  # assigns IDs without committing

    log.info(
        "form_fields.replaced",
        job_id=job_id,
        count=len(new_fields),
        updated_by=current_user.email,
    )

    return [_to_read(f) for f in new_fields]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_read(f: JobFormField) -> FormFieldRead:
    return FormFieldRead(
        id=f.id,
        label=f.label,
        field_type=f.field_type,
        is_required=f.is_required,
        options=f.options,
        order=f.order,
    )
