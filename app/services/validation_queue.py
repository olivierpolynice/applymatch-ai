import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    JobOffer,
    MatchResult,
    ValidationQueueItem,
)
from app.services.notifications import (
    create_notification_once,
)


logger = logging.getLogger(__name__)


class ValidationQueueError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_queue_item_or_error(
    db: Session,
    item_id: int,
) -> ValidationQueueItem:
    item = db.get(
        ValidationQueueItem,
        item_id,
    )

    if item is None:
        raise ValidationQueueError(
            "Validation queue item not found",
            status_code=404,
        )

    return item


def get_match_result_or_error(
    db: Session,
    match_result_id: int,
) -> MatchResult:
    match_result = db.get(
        MatchResult,
        match_result_id,
    )

    if match_result is None:
        raise ValidationQueueError(
            "Match result not found",
            status_code=404,
        )

    return match_result


def create_validation_notification(
    db: Session,
    *,
    item: ValidationQueueItem,
) -> None:
    offer = db.get(
        JobOffer,
        item.offer_id,
    )

    offer_title = (
        offer.title
        if offer is not None
        else f"Offre numéro {item.offer_id}"
    )

    company = (
        offer.company
        if offer is not None
        else "Entreprise inconnue"
    )

    try:
        create_notification_once(
            db,
            notification_type=(
                "validation_required"
            ),
            level="warning",
            title=(
                f"Validation requise : {offer_title}"
            )[:200],
            message=(
                f"{company} · Cette candidature "
                f"est en attente de validation "
                f"manuelle. Priorité : "
                f"{item.priority}."
            ),
            target_url=(
                f"#validation-{item.id}"
            ),
        )
    except Exception:
        db.rollback()

        logger.exception(
            (
                "Unable to create validation "
                "notification for queue item %s."
            ),
            item.id,
        )


def create_validation_queue_item(
    db: Session,
    match_result_id: int,
) -> ValidationQueueItem:
    match_result = get_match_result_or_error(
        db,
        match_result_id,
    )

    if match_result.decision == "rejected":
        raise ValidationQueueError(
            (
                "This match is not eligible for "
                "manual validation"
            ),
            status_code=422,
        )

    existing_item = db.scalar(
        select(ValidationQueueItem).where(
            ValidationQueueItem.match_result_id
            == match_result.id
        )
    )

    if existing_item is not None:
        raise ValidationQueueError(
            (
                "This match is already in the "
                "validation queue"
            ),
            status_code=409,
        )

    item = ValidationQueueItem(
        profile_id=match_result.profile_id,
        offer_id=match_result.offer_id,
        match_result_id=match_result.id,
        status="pending",
        priority=(
            match_result.application_priority
        ),
    )

    db.add(item)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()

        raise ValidationQueueError(
            (
                "This match is already in the "
                "validation queue"
            ),
            status_code=409,
        ) from error

    db.refresh(item)

    create_validation_notification(
        db,
        item=item,
    )

    return item


def decide_validation_queue_item(
    db: Session,
    item_id: int,
    decision: str,
    reviewer_comment: str | None,
) -> ValidationQueueItem:
    item = get_queue_item_or_error(
        db,
        item_id,
    )

    if item.status != "pending":
        raise ValidationQueueError(
            (
                "This validation queue item has "
                "already been decided"
            ),
            status_code=409,
        )

    item.status = decision
    item.reviewer_comment = reviewer_comment
    item.decided_at = utc_now()

    db.commit()
    db.refresh(item)

    return item
