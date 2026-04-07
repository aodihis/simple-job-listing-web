from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApplicationEducation(Base):
    __tablename__ = "application_education"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )

    institution: Mapped[str] = mapped_column(String(300), nullable=False)
    degree: Mapped[str] = mapped_column(String(100), nullable=False)
    field_of_study: Mapped[str | None] = mapped_column(String(200), nullable=True)
    gpa: Mapped[str | None] = mapped_column(String(20), nullable=True)
    start_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_year: Mapped[int | None] = mapped_column(Integer, nullable=True)  # None = present

    def __repr__(self) -> str:
        return (
            f"<ApplicationEducation id={self.id} application_id={self.application_id} "
            f"institution={self.institution!r} degree={self.degree!r}>"
        )
