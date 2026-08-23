from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    full_name: Mapped[str] = mapped_column(
        String(150),
    )
    education_level: Mapped[str] = mapped_column(
        String(100),
    )
    program: Mapped[str] = mapped_column(
        String(200),
    )

    target_contract: Mapped[str] = mapped_column(
        String(100),
    )
    availability: Mapped[str] = mapped_column(
        String(100),
    )
    work_schedule: Mapped[str] = mapped_column(
        String(100),
    )
    location: Mapped[str] = mapped_column(
        String(150),
    )

    target_roles: Mapped[str] = mapped_column(Text)
    skills: Mapped[str] = mapped_column(Text)

    professional_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    experience_highlights: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    project_highlights: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    portfolio_url: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )