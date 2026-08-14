from datetime import datetime, timezone

from sqlalchemy import (
    func,
    select,
    update,
)
from sqlalchemy.orm import Session

from app.models import Notification
from app.schemas import (
    NotificationLevel,
    NotificationType,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_notification(
    db: Session,
    *,
    notification_type: NotificationType,
    title: str,
    message: str,
    level: NotificationLevel = "info",
    target_url: str | None = None,
) -> Notification:
    notification = Notification(
        notification_type=notification_type,
        level=level,
        title=title,
        message=message,
        target_url=target_url,
        is_read=False,
    )

    db.add(notification)
    db.commit()
    db.refresh(notification)

    return notification

def create_notification_once(
    db: Session,
    *,
    notification_type: NotificationType,
    title: str,
    message: str,
    level: NotificationLevel = "info",
    target_url: str,
) -> tuple[Notification, bool]:
    existing_notification = db.scalar(
        select(Notification).where(
            Notification.notification_type
            == notification_type,
            Notification.target_url
            == target_url,
        )
    )

    if existing_notification is not None:
        return existing_notification, False

    notification = create_notification(
        db,
        notification_type=notification_type,
        title=title,
        message=message,
        level=level,
        target_url=target_url,
    )

    return notification, True
def list_notifications(
    db: Session,
    *,
    limit: int = 20,
    unread_only: bool = False,
    notification_type: (
        NotificationType | None
    ) = None,
) -> list[Notification]:
    statement = (
        select(Notification)
        .order_by(
            Notification.created_at.desc(),
            Notification.id.desc(),
        )
        .limit(limit)
    )

    if unread_only:
        statement = statement.where(
            Notification.is_read.is_(False),
        )

    if notification_type is not None:
        statement = statement.where(
            Notification.notification_type
            == notification_type,
        )

    return list(db.scalars(statement))


def count_unread_notifications(
    db: Session,
) -> int:
    statement = (
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.is_read.is_(False),
        )
    )

    return int(
        db.scalar(statement) or 0
    )


def get_notification(
    db: Session,
    notification_id: int,
) -> Notification | None:
    return db.get(
        Notification,
        notification_id,
    )


def mark_notification_as_read(
    db: Session,
    notification: Notification,
) -> Notification:
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = utc_now()

        db.commit()
        db.refresh(notification)

    return notification


def mark_all_notifications_as_read(
    db: Session,
) -> int:
    unread_count = count_unread_notifications(db)

    if unread_count == 0:
        return 0

    db.execute(
        update(Notification)
        .where(
            Notification.is_read.is_(False),
        )
        .values(
            is_read=True,
            read_at=utc_now(),
        )
    )
    db.commit()

    return unread_count