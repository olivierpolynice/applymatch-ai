from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GmailDelivery(Base):
    __tablename__ = "gmail_deliveries"

    id: Mapped[int] = mapped_column(primary_key=True)
    draft_id: Mapped[int] = mapped_column(
        ForeignKey("application_drafts.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    recipient: Mapped[str] = mapped_column(String(320))
    gmail_draft_id: Mapped[str] = mapped_column(String(255), unique=True)
    gmail_message_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default="draft_created", index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

