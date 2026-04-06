from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.logging.config import get_logger
from app.models.job import Job, Tag
from app.models.user import AdminUser
from app.schemas.job import JobCreate, JobUpdate
from app.utils.exceptions import NotFoundError

log = get_logger(__name__)


def _get_or_create_tags(db: Session, tag_names: list[str]) -> list[Tag]:
    """Return Tag ORM objects for each name, creating new ones as needed."""
    tags: list[Tag] = []
    for name in tag_names:
        tag = db.query(Tag).filter(Tag.name == name).first()
        if tag is None:
            tag = Tag(name=name)
            db.add(tag)
        tags.append(tag)
    return tags


def create_job(db: Session, data: JobCreate, posted_by: AdminUser) -> Job:
    tags = _get_or_create_tags(db, data.tags)

    job = Job(
        title=data.title,
        description=data.description,
        employment_type=data.employment_type.value,
        location=data.location,
        is_remote=data.is_remote,
        application_mode=data.application_mode.value,
        external_apply_url=data.external_apply_url,
        is_active=True,
        is_deleted=False,
        posted_by=posted_by,
        expires_at=data.expires_at,
        tags=tags,
    )
    db.add(job)
    db.flush()  # populate public_id and server-default timestamps before returning

    log.info(
        "job.created",
        title=data.title,
        employment_type=data.employment_type.value,
        posted_by=posted_by.email,
        tags=data.tags,
    )
    return job


def update_job(db: Session, public_id: str, data: JobUpdate, updated_by: AdminUser) -> Job:
    job = get_job_by_public_id(db, public_id)

    job.title = data.title
    job.description = data.description
    job.employment_type = data.employment_type.value
    job.location = data.location
    job.is_remote = data.is_remote
    job.application_mode = data.application_mode.value
    job.external_apply_url = data.external_apply_url
    job.expires_at = data.expires_at
    job.tags = _get_or_create_tags(db, data.tags)

    log.info("job.updated", public_id=public_id, updated_by=updated_by.email)
    return job


def list_jobs_admin(
    db: Session,
    *,
    include_deleted: bool = False,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Job], int]:
    """Return paginated jobs for the admin view (includes inactive by default)."""
    query = db.query(Job)
    if not include_deleted:
        query = query.filter(Job.is_deleted == False)  # noqa: E712
    query = query.order_by(Job.created_at.desc())

    total = query.count()
    jobs = query.offset((page - 1) * per_page).limit(per_page).all()
    return jobs, total


def get_job_by_public_id(db: Session, public_id: str) -> Job:
    job = db.query(Job).filter(Job.public_id == public_id, Job.is_deleted == False).first()  # noqa: E712
    if job is None:
        raise NotFoundError(f"Job '{public_id}' not found.")
    return job


def list_jobs_public(
    db: Session,
    *,
    q: str | None = None,
    tags: list[str] | None = None,
    employment_type: str | None = None,
    is_remote: bool | None = None,
    sort: str = "newest",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Job], int]:
    """Return paginated active jobs for the public site, with optional filters."""
    now = datetime.now(timezone.utc)
    query = (
        db.query(Job)
        .filter(
            Job.is_active == True,  # noqa: E712
            Job.is_deleted == False,  # noqa: E712
        )
        .filter((Job.expires_at == None) | (Job.expires_at > now))  # noqa: E711
    )

    if q:
        search = f"%{q}%"
        query = query.filter((Job.title.ilike(search)) | (Job.description.ilike(search)))

    if employment_type:
        query = query.filter(Job.employment_type == employment_type)

    if is_remote is not None:
        query = query.filter(Job.is_remote == is_remote)

    if tags:
        for tag_name in tags:
            query = query.filter(Job.tags.any(Tag.name == tag_name))

    if sort == "oldest":
        query = query.order_by(Job.created_at.asc())
    else:
        query = query.order_by(Job.created_at.desc())

    total = query.count()
    jobs = query.offset((page - 1) * per_page).limit(per_page).all()
    return jobs, total


def get_public_job(db: Session, public_id: str) -> Job:
    """Return a single active, non-deleted job by public_id. Raises NotFoundError otherwise."""
    now = datetime.now(timezone.utc)
    job = (
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
        raise NotFoundError(f"Job '{public_id}' not found.")
    return job


def toggle_job_active(db: Session, public_id: str, toggled_by: AdminUser) -> Job:
    """Flip is_active on a job. Raises NotFoundError if job is deleted or not found."""
    job = get_job_by_public_id(db, public_id)
    job.is_active = not job.is_active
    log.info(
        "job.toggled",
        public_id=public_id,
        is_active=job.is_active,
        toggled_by=toggled_by.email,
    )
    return job


def delete_job(db: Session, public_id: str, deleted_by: AdminUser) -> Job:
    """Soft-delete a job by setting is_deleted=True. Raises NotFoundError if already deleted."""
    job = get_job_by_public_id(db, public_id)
    job.is_deleted = True
    job.is_active = False
    log.info("job.deleted", public_id=public_id, deleted_by=deleted_by.email)
    return job
