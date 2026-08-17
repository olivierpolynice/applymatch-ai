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
from app.models import ApplicationDraft
from app.schemas import (
    ApplicationDraftCreate,
    ApplicationDraftRead,
    ApplicationDraftUpdate,
)
from app.services.application_drafts import (
    ApplicationDraftError,
    create_application_draft,
    get_draft_or_error,
    regenerate_application_draft,
    update_application_draft,
)


router = APIRouter(
    prefix="/application-drafts",
    tags=["Application drafts"],
    dependencies=[
        Depends(get_current_admin),
    ],
)


def handle_draft_error(
    error: ApplicationDraftError,
) -> HTTPException:
    return HTTPException(
        status_code=error.status_code,
        detail=error.message,
    )


@router.post(
    "",
    response_model=ApplicationDraftRead,
    status_code=201,
)
def create_draft(
    data: ApplicationDraftCreate,
    db: Session = Depends(get_db),
) -> ApplicationDraft:
    try:
        return create_application_draft(
            db=db,
            validation_queue_item_id=(
                data.validation_queue_item_id
            ),
        )
    except ApplicationDraftError as error:
        raise handle_draft_error(error) from error


@router.get(
    "",
    response_model=list[ApplicationDraftRead],
)
def list_drafts(
    status_filter: str | None = Query(
        default=None,
        alias="status",
    ),
    profile_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[ApplicationDraft]:
    statement = select(
        ApplicationDraft
    ).order_by(
        ApplicationDraft.updated_at.desc(),
    )

    if status_filter is not None:
        statement = statement.where(
            ApplicationDraft.status
            == status_filter
        )

    if profile_id is not None:
        statement = statement.where(
            ApplicationDraft.profile_id
            == profile_id
        )

    return list(db.scalars(statement))


@router.get(
    "/{draft_id}",
    response_model=ApplicationDraftRead,
)
def get_draft(
    draft_id: int,
    db: Session = Depends(get_db),
) -> ApplicationDraft:
    try:
        return get_draft_or_error(
            db,
            draft_id,
        )
    except ApplicationDraftError as error:
        raise handle_draft_error(error) from error


@router.patch(
    "/{draft_id}",
    response_model=ApplicationDraftRead,
)
def update_draft(
    draft_id: int,
    data: ApplicationDraftUpdate,
    db: Session = Depends(get_db),
) -> ApplicationDraft:
    try:
        return update_application_draft(
            db=db,
            draft_id=draft_id,
            update_data=data.model_dump(
                exclude_unset=True,
            ),
        )
    except ApplicationDraftError as error:
        raise handle_draft_error(error) from error


@router.post(
    "/{draft_id}/regenerate",
    response_model=ApplicationDraftRead,
)
def regenerate_draft(
    draft_id: int,
    db: Session = Depends(get_db),
) -> ApplicationDraft:
    try:
        return regenerate_application_draft(
            db=db,
            draft_id=draft_id,
        )
    except ApplicationDraftError as error:
        raise handle_draft_error(error) from error