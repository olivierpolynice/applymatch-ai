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


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    notification_type: Mapped[str] = mapped_column(
        String(50),
        index=True,
    )

    level: Mapped[str] = mapped_column(
        String(20),
        default="info",
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(200),
    )

    message: Mapped[str] = mapped_column(
        Text,
    )

    target_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        index=True,
    )

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
    )