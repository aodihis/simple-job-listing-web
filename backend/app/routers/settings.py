from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field

from app.dependencies import require_active_admin
from app.logging.config import get_logger
from app.services import email_service

log = get_logger(__name__)

router = APIRouter(prefix="/api/v1/admin/settings", tags=["Admin — Settings"])


class TestEmailRequest(BaseModel):
    to: EmailStr = Field(description="Recipient address for the test email")


class TestEmailResponse(BaseModel):
    success: bool = Field(description="Whether the test email was sent successfully")
    message: str = Field(description="Human-readable result message")


@router.post(
    "/test-email",
    response_model=TestEmailResponse,
    summary="Send a test email",
    description=(
        "Sends a test email using the current SMTP configuration. "
        "Returns a success/failure result without raising HTTP errors, "
        "so the client always receives a structured response."
    ),
    dependencies=[Depends(require_active_admin)],
)
def test_email(body: TestEmailRequest) -> TestEmailResponse:
    try:
        email_service.send_test_email(body.to)
        return TestEmailResponse(success=True, message="Test email sent successfully.")
    except Exception as exc:
        log.warning("email.test_failed", to=body.to, error=str(exc))
        return TestEmailResponse(success=False, message=str(exc))
