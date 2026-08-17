from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth_dependencies import (
    get_current_admin,
)
from app.db.session import get_db
from app.models import ValidationQueueItem
from app.schemas import (
    ValidationQueueCreate,
    ValidationQueueDecisionUpdate,
    ValidationQueueRead,
)
from app.services.validation_queue import (
    ValidationQueueError,
    create_validation_queue_item,
    decide_validation_queue_item,
    get_queue_item_or_error,
)


router = APIRouter(
    prefix="/validation-queue",
    tags=["Validation queue"],
    dependencies=[
        Depends(get_current_admin),
    ],
)


def handle_validation_error(
    error: ValidationQueueError,
) -> HTTPException:
    return HTTPException(
        status_code=error.status_code,
        detail=error.message,
    )


@router.post(
    "",
    response_model=ValidationQueueRead,
    status_code=201,
)
def add_to_validation_queue(
    data: ValidationQueueCreate,
    db: Session = Depends(get_db),
) -> ValidationQueueItem:
    try:
        return create_validation_queue_item(
            db=db,
            match_result_id=data.match_result_id,
        )
    except ValidationQueueError as error:
        raise handle_validation_error(error) from error


@router.get(
    "",
    response_model=list[ValidationQueueRead],
)
def list_validation_queue(
    status_filter: str | None = Query(
        default=None,
        alias="status",
    ),
    priority: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[ValidationQueueItem]:
    statement = select(
        ValidationQueueItem
    ).order_by(
        ValidationQueueItem.created_at.desc(),
    )

    if status_filter is not None:
        statement = statement.where(
            ValidationQueueItem.status
            == status_filter
        )

    if priority is not None:
        statement = statement.where(
            ValidationQueueItem.priority
            == priority
        )

    return list(db.scalars(statement))


@router.get(
    "/{item_id}",
    response_model=ValidationQueueRead,
)
def get_validation_queue_item(
    item_id: int,
    db: Session = Depends(get_db),
) -> ValidationQueueItem:
    try:
        return get_queue_item_or_error(
            db,
            item_id,
        )
    except ValidationQueueError as error:
        raise handle_validation_error(error) from error


@router.patch(
    "/{item_id}/decision",
    response_model=ValidationQueueRead,
)
def decide_validation_queue(
    item_id: int,
    data: ValidationQueueDecisionUpdate,
    db: Session = Depends(get_db),
) -> ValidationQueueItem:
    try:
        return decide_validation_queue_item(
            db=db,
            item_id=item_id,
            decision=data.decision,
            reviewer_comment=(
                data.reviewer_comment
            ),
        )
    except ValidationQueueError as error:
        raise handle_validation_error(error) from error