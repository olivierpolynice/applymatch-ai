from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CollectorRun(Base):
    __tablename__ = "collector_runs"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    collector: Mapped[str] = mapped_column(
        String(100),
        default="la-bonne-alternance",
        index=True,
    )

    trigger: Mapped[str] = mapped_column(
        String(20),
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="running",
        index=True,
    )

    found: Mapped[int] = mapped_column(
        default=0,
    )
    added: Mapped[int] = mapped_column(
        default=0,
    )
    duplicates: Mapped[int] = mapped_column(
        default=0,
    )
    errors: Mapped[int] = mapped_column(
        default=0,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )