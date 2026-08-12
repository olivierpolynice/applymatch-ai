from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MatchResult(Base):
    __tablename__ = "match_results"
    __table_args__ = (
        UniqueConstraint(
            "profile_id",
            "offer_id",
            name="uq_match_results_profile_offer",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
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

    score: Mapped[int]
    recommendation: Mapped[str] = mapped_column(
        String(100),
    )
    confidence: Mapped[str] = mapped_column(
        String(20),
        default="faible",
    )

    matched_skills: Mapped[list[str]] = mapped_column(JSON)
    skills_to_strengthen: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
    )
    missing_skills: Mapped[list[str]] = mapped_column(JSON)

    skills_score: Mapped[int]
    role_score: Mapped[int]
    contract_score: Mapped[int]
    location_score: Mapped[int]
    education_score: Mapped[int] = mapped_column(default=0)

    role_match: Mapped[bool] = mapped_column(Boolean)
    contract_match: Mapped[bool] = mapped_column(Boolean)
    location_match: Mapped[bool] = mapped_column(Boolean)
    education_match: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
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