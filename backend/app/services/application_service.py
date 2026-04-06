from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.logging.config import get_logger
from app.models.application import Application
from app.models.form_field import JobFormField
from app.models.job import Job
from app.schemas.application import ApplicationCreate, ApplicationConfirmation, ApplicationRead, ApplicationStatus
from app.utils.exceptions import BadRequestError, ConflictError, NotFoundError

log = get_logger(__name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_URL_RE = re.compile(r"^https?://\S+$")


def submit_application(
    db: Session,
    job_public_id: str,
    data: ApplicationCreate,
) -> ApplicationConfirmation:
    """
    Validate and persist a new application for a job.

    Rules enforced:
    - The job must be active, not deleted, and not expired.
    - The job must use application_mode='form' (not 'external_url').
    - One submission per (job, email) pair.
    - Every required form field must have a non-empty answer.
    - Radio / select values must be one of the configured options.
    - Checkbox values must all be within the configured options.
    - Email-type fields must contain a valid email address.
    - URL-type fields must start with http:// or https://.
    """
    job = _get_open_job(db, job_public_id)

    # Prevent duplicate submissions
    existing = (
        db.query(Application)
        .filter(
            Application.job_id == job.id,
            Application.applicant_email == data.applicant_email.lower(),
        )
        .first()
    )
    if existing:
        raise ConflictError("You have already submitted an application for this job.")

    # Validate dynamic field responses
    _validate_responses(job.form_fields, data.responses)

    application = Application(
        job_id=job.id,
        applicant_name=data.applicant_name,
        applicant_email=data.applicant_email.lower(),
    )
    application.responses = data.responses
    db.add(application)
    db.flush()  # populate application.public_id before returning

    log.info(
        "application.submitted",
        job_id=job_public_id,
        application_id=application.public_id,
        email=data.applicant_email,
    )

    return ApplicationConfirmation(public_id=application.public_id)


# ── Admin service functions ───────────────────────────────────────────────────

def list_applications(
    db: Session,
    *,
    job_public_id: str | None = None,
    status: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[ApplicationRead], int]:
    """
    Return a paginated list of applications.

    Optionally filter by job public_id and/or status.
    Returns (items, total_count).
    """
    query = db.query(Application).join(Application.job)

    if job_public_id:
        query = query.filter(Job.public_id == job_public_id)
    if status:
        query = query.filter(Application.status == status)

    total: int = query.count()
    applications = (
        query.order_by(Application.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return [_to_read(a) for a in applications], total


def get_application(db: Session, public_id: str) -> ApplicationRead:
    """Return a single application by its public_id, or raise NotFoundError."""
    application = _get_by_public_id(db, public_id)
    return _to_read(application)


def update_application_status(
    db: Session,
    public_id: str,
    new_status: ApplicationStatus,
) -> ApplicationRead:
    """Update the workflow status of an application."""
    application = _get_by_public_id(db, public_id)
    old_status = application.status
    application.status = new_status.value

    log.info(
        "application.status_updated",
        application_id=public_id,
        old_status=old_status,
        new_status=new_status.value,
    )

    return _to_read(application)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_open_job(db: Session, public_id: str) -> Job:
    """Return an active, non-expired, form-mode job, or raise NotFoundError."""
    now = datetime.now(timezone.utc)
    job: Job | None = (
        db.query(Job)
        .filter(
            Job.public_id == public_id,
            Job.is_active == True,  # noqa: E712
            Job.is_deleted == False,  # noqa: E712
        )
        .filter((Job.expires_at == None) | (Job.expires_at > now))  # noqa: E711
        .first()
    )
    if job is None:
        raise NotFoundError("Job not found or no longer accepting applications.")
    if job.application_mode != "form":
        raise NotFoundError("This job does not accept applications through this site.")
    return job


def _validate_responses(
    form_fields: list[JobFormField],
    responses: dict[str, str | list[str]],
) -> None:
    """
    Validate each form field answer.  Raises BadRequestError on the first violation.
    """
    for field in form_fields:
        key = str(field.id)
        raw = responses.get(key)

        empty = (
            raw is None
            or (isinstance(raw, str) and not raw.strip())
            or (isinstance(raw, list) and not raw)
        )

        if field.is_required and empty:
            raise BadRequestError(f"'{field.label}' is required.")

        if empty:
            continue  # optional field left blank — nothing to validate

        ft = field.field_type

        if ft in ("radio", "select"):
            if not isinstance(raw, str):
                raise BadRequestError(f"'{field.label}' must be a single value.")
            if raw not in field.options:
                raise BadRequestError(
                    f"'{raw}' is not a valid choice for '{field.label}'."
                )

        elif ft == "checkbox":
            if not isinstance(raw, list):
                raise BadRequestError(f"'{field.label}' must be a list of values.")
            bad = [v for v in raw if v not in field.options]
            if bad:
                raise BadRequestError(
                    f"Invalid choices for '{field.label}': {', '.join(bad)}"
                )

        elif ft == "email":
            if not isinstance(raw, str) or not _EMAIL_RE.match(raw):
                raise BadRequestError(f"'{field.label}' must be a valid email address.")

        elif ft == "url":
            if not isinstance(raw, str) or not _URL_RE.match(raw):
                raise BadRequestError(
                    f"'{field.label}' must be a valid URL starting with http:// or https://"
                )

        elif ft == "number":
            if isinstance(raw, str):
                try:
                    float(raw)
                except ValueError:
                    raise BadRequestError(f"'{field.label}' must be a number.")


def _get_by_public_id(db: Session, public_id: str) -> Application:
    """Return an Application by public_id or raise NotFoundError."""
    application: Application | None = (
        db.query(Application).filter(Application.public_id == public_id).first()
    )
    if application is None:
        raise NotFoundError("Application not found.")
    return application


def _to_read(application: Application) -> ApplicationRead:
    """Convert an Application ORM object to an ApplicationRead schema."""
    return ApplicationRead(
        public_id=application.public_id,
        applicant_name=application.applicant_name,
        applicant_email=application.applicant_email,
        responses=application.responses,
        status=application.status,
        created_at=application.created_at,
        job_public_id=application.job.public_id,
        job_title=application.job.title,
    )
