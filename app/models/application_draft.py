from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ApplicationDraft(Base):
    __tablename__ = "application_drafts"
    __table_args__ = (
        UniqueConstraint(
            "validation_queue_item_id",
            name=(
                "uq_application_drafts_validation_queue_item"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    validation_queue_item_id: Mapped[int] = mapped_column(
        ForeignKey(
            "validation_queue_items.id",
            ondelete="CASCADE",
        ),
        index=True,
    )
    profile_id: Mapped[int] = mapped_column(
        ForeignKey(
            "candidate_profiles.id",
            ondelete="CASCADE",
        ),
        index=True,
    )
    offer_id: Mapped[int] = mapped_column(
        ForeignKey(
            "job_offers.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
        index=True,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
    )

    cover_letter: Mapped[str] = mapped_column(Text)
    short_message: Mapped[str] = mapped_column(Text)
    cv_adaptation_tips: Mapped[str] = mapped_column(Text)

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
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