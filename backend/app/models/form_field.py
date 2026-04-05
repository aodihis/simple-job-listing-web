from __future__ import annotations

import json

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class JobFormField(Base):
    __tablename__ = "form_fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Display order (0-based). The service always writes a contiguous sequence.
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    label: Mapped[str] = mapped_column(String(200), nullable=False)

    # Allowed values: text | textarea | email | url | number | radio | select | checkbox
    field_type: Mapped[str] = mapped_column(String(20), nullable=False)

    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # JSON-encoded list[str] — only populated for radio / select / checkbox types.
    # Stored inline; never executed. Max 20 items, each ≤ 100 chars (enforced by schema).
    _options_json: Mapped[str] = mapped_column(
        "options_json", Text, nullable=False, default="[]"
    )

    job: Mapped[object] = relationship("Job", back_populates="form_fields")

    # ── Python-level helpers ────────────────────────────────────────────────

    @property
    def options(self) -> list[str]:
        try:
            value = json.loads(self._options_json)
            return value if isinstance(value, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    @options.setter
    def options(self, value: list[str]) -> None:
        self._options_json = json.dumps(value)

    def __repr__(self) -> str:
        return (
            f"<JobFormField id={self.id} job_id={self.job_id} "
            f"type={self.field_type!r} label={self.label!r}>"
        )
