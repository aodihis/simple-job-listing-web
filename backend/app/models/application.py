from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.application_education import ApplicationEducation
from app.models.application_experience import ApplicationExperience


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )

    job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    applicant_name: Mapped[str] = mapped_column(String(200), nullable=False)
    applicant_email: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    # JSON-encoded dict[str, str | list[str]]
    # Keys are str(form_field.id); values are the applicant's answers.
    _responses_json: Mapped[str] = mapped_column(
        "responses_json", Text, nullable=False, default="{}"
    )

    # CV / resume upload
    cv_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cv_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Workflow status: new → reviewed → rejected | hired
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="new")

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    job = relationship("Job", back_populates="applications")
    education: Mapped[list[ApplicationEducation]] = relationship(
        "ApplicationEducation", cascade="all, delete-orphan", lazy="selectin"
    )
    experience: Mapped[list[ApplicationExperience]] = relationship(
        "ApplicationExperience", cascade="all, delete-orphan", lazy="selectin"
    )

    # ── Python-level helpers ────────────────────────────────────────────────

    @property
    def responses(self) -> dict[str, str | list[str]]:
        try:
            value = json.loads(self._responses_json)
            return value if isinstance(value, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    @responses.setter
    def responses(self, value: dict[str, str | list[str]]) -> None:
        self._responses_json = json.dumps(value)

    def __repr__(self) -> str:
        return (
            f"<Application id={self.id} job_id={self.job_id} "
            f"email={self.applicant_email!r} status={self.status!r}>"
        )
