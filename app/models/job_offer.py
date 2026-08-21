from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class JobOffer(Base):
    __tablename__ = "job_offers"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "external_id",
            name="uq_job_offers_source_external_id",
        ),
        UniqueConstraint(
            "provider_confirmation_id",
            name="uq_job_offers_provider_confirmation_id",
        ),
        CheckConstraint(
            "experience_min IS NULL OR experience_min >= 0",
            name="ck_job_offers_experience_min_non_negative",
        ),
        CheckConstraint(
            "experience_max IS NULL OR experience_max >= 0",
            name="ck_job_offers_experience_max_non_negative",
        ),
        CheckConstraint(
            "experience_min IS NULL OR experience_max IS NULL "
            "OR experience_min <= experience_max",
            name="ck_job_offers_experience_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    title: Mapped[str] = mapped_column(
        String(200),
        index=True,
    )
    company: Mapped[str] = mapped_column(
        String(150),
        index=True,
    )
    location: Mapped[str] = mapped_column(
        String(150),
    )
    contract_type: Mapped[str] = mapped_column(
        String(100),
    )
    description: Mapped[str] = mapped_column(Text)

    source: Mapped[str] = mapped_column(
        String(100),
    )
    external_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    source_url: Mapped[str | None] = mapped_column(
        String(1000),
        unique=True,
        nullable=True,
    )
    fingerprint: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="new",
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    experience_min: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    experience_max: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    application_channel: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )
    application_status: Mapped[str] = mapped_column(
        String(40),
        default="not_started",
        index=True,
    )
    provider_confirmation_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
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
