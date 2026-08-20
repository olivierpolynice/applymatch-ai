from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ApplicationArchive(Base):
    __tablename__ = "application_archives"

    id: Mapped[int] = mapped_column(primary_key=True)
    draft_id: Mapped[int] = mapped_column(
        ForeignKey("application_drafts.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    profile_id: Mapped[int] = mapped_column(index=True)
    offer_id: Mapped[int] = mapped_column(index=True)
    company: Mapped[str] = mapped_column(String(150))
    offer_title: Mapped[str] = mapped_column(String(200))
    application_mode: Mapped[str] = mapped_column(String(20))
    channel: Mapped[str] = mapped_column(String(40))
    provider_confirmation_id: Mapped[str] = mapped_column(
        String(255), unique=True
    )
    cv_snapshot: Mapped[str] = mapped_column(Text)
    cover_letter_snapshot: Mapped[str] = mapped_column(Text)
    short_message_snapshot: Mapped[str] = mapped_column(Text)
    proposed_answers_snapshot: Mapped[list[dict[str, str]]] = mapped_column(
        JSON, default=list
    )
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
