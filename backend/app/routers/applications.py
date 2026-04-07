from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_active_admin
from app.models.user import AdminUser
from app.schemas.application import ApplicationRead, ApplicationStatus
from app.services import application_service

router = APIRouter(prefix="/api/v1/admin/applications", tags=["Admin — Applications"])


class StatusUpdate:
    """Request body for PATCH status endpoint."""

    def __init__(self, status: ApplicationStatus) -> None:
        self.status = status


from pydantic import BaseModel  # noqa: E402  (local import for schema only)


class StatusUpdateBody(BaseModel):
    status: ApplicationStatus


@router.get(
    "",
    response_model=dict,
    summary="List applications (admin)",
    description=(
        "Returns paginated applications. "
        "Filter by job public_id and/or status. "
        "Sorted newest first."
    ),
)
def list_applications(
    job_id: str | None = Query(default=None, description="Filter by job public_id."),
    status: ApplicationStatus | None = Query(default=None, description="Filter by status."),
    page: int = Query(default=1, ge=1, description="Page number."),
    per_page: int = Query(default=20, ge=1, le=100, description="Items per page."),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_active_admin),
) -> dict:
    items, total = application_service.list_applications(
        db,
        job_public_id=job_id,
        status=status.value if status else None,
        page=page,
        per_page=per_page,
    )
    return {
        "items": [i.model_dump() for i in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, -(-total // per_page)),
    }


@router.get(
    "/{application_id}",
    response_model=ApplicationRead,
    summary="Get application detail (admin)",
    description="Returns full application detail including all form responses.",
)
def get_application(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_active_admin),
) -> ApplicationRead:
    return application_service.get_application(db, application_id)


@router.get(
    "/{application_id}/cv",
    summary="Download application CV (admin)",
    description="Stream the CV file attached to an application. Returns 404 if no CV was uploaded.",
)
def download_cv(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_active_admin),
) -> Response:
    data, cv_filename = application_service.get_application_cv(db, application_id)
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{cv_filename}"'},
    )


@router.patch(
    "/{application_id}/status",
    response_model=ApplicationRead,
    summary="Update application status",
    description=(
        "Update the workflow status of an application. "
        "Allowed values: new, reviewed, rejected, hired."
    ),
)
def update_status(
    application_id: str,
    body: StatusUpdateBody,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_active_admin),
) -> ApplicationRead:
    return application_service.update_application_status(db, application_id, body.status)
