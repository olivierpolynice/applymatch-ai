from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import (
    NotificationRead,
    NotificationType,
    NotificationUnreadCountRead,
)
from app.services.notifications import (
    count_unread_notifications,
    get_notification,
    list_notifications,
    mark_all_notifications_as_read,
    mark_notification_as_read,
)


router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


@router.get(
    "",
    response_model=list[NotificationRead],
)
def get_notifications(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    unread_only: bool = Query(
        default=False,
    ),
    notification_type: (
        NotificationType | None
    ) = Query(
        default=None,
    ),
    db: Session = Depends(get_db),
) -> list:
    return list_notifications(
        db,
        limit=limit,
        unread_only=unread_only,
        notification_type=notification_type,
    )


@router.get(
    "/unread-count",
    response_model=NotificationUnreadCountRead,
)
def get_unread_count(
    db: Session = Depends(get_db),
) -> NotificationUnreadCountRead:
    return NotificationUnreadCountRead(
        unread_count=(
            count_unread_notifications(db)
        ),
    )


@router.patch(
    "/read-all",
    response_model=NotificationUnreadCountRead,
)
def read_all_notifications(
    db: Session = Depends(get_db),
) -> NotificationUnreadCountRead:
    mark_all_notifications_as_read(db)

    return NotificationUnreadCountRead(
        unread_count=0,
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationRead,
)
def read_notification(
    notification_id: int,
    db: Session = Depends(get_db),
):
    notification = get_notification(
        db,
        notification_id,
    )

    if notification is None:
        raise HTTPException(
            status_code=404,
            detail="Notification not found",
        )

    return mark_notification_as_read(
        db,
        notification,
    )