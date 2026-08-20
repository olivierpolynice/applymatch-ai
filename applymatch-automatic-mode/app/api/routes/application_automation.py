from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth_dependencies import get_current_admin
from app.db.session import get_db
from app.models import ApplicationArchive
from app.schemas import (
    ApplicationArchiveRead,
    AutomationEvaluationCreate,
    AutomationEvaluationRead,
    ConfirmApplicationSentCreate,
)
from app.services.application_automation import (
    ApplicationAutomationError,
    archive_confirmed_application,
    evaluate_automation,
)


router = APIRouter(
    prefix="/application-automation",
    tags=["Application automation"],
    dependencies=[Depends(get_current_admin)],
)


def as_http_error(error: ApplicationAutomationError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=error.message)


@router.post("/evaluate", response_model=AutomationEvaluationRead)
def evaluate(
    data: AutomationEvaluationCreate,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return evaluate_automation(db, **data.model_dump())
    except ApplicationAutomationError as error:
        raise as_http_error(error) from error


@router.post(
    "/confirm-sent",
    response_model=ApplicationArchiveRead,
    status_code=201,
)
def confirm_sent(
    data: ConfirmApplicationSentCreate,
    db: Session = Depends(get_db),
) -> ApplicationArchive:
    try:
        return archive_confirmed_application(db, **data.model_dump())
    except ApplicationAutomationError as error:
        raise as_http_error(error) from error


@router.get("/archives", response_model=list[ApplicationArchiveRead])
def list_archives(db: Session = Depends(get_db)) -> list[ApplicationArchive]:
    return list(
        db.scalars(
            select(ApplicationArchive).order_by(
                ApplicationArchive.sent_at.desc()
            )
        )
    )
