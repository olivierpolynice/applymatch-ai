from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ValidationQueueItem(Base):
    __tablename__ = "validation_queue_items"
    __table_args__ = (
        UniqueConstraint(
            "profile_id",
            "offer_id",
            name=(
                "uq_validation_queue_items_profile_offer"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
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
    match_result_id: Mapped[int] = mapped_column(
        ForeignKey(
            "match_results.id",
            ondelete="CASCADE",
        ),
        unique=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(20),
    )

    reviewer_comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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