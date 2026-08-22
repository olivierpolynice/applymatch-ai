from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth_dependencies import get_current_admin
from app.db.session import get_db
from app.schemas import BrowserAssistanceRead
from app.services.browser_assistance import (
    BrowserAssistanceError,
    prepare_browser_assistance,
)


router = APIRouter(
    prefix="/browser-assistance",
    tags=["Browser assistance"],
    dependencies=[Depends(get_current_admin)],
)


@router.post(
    "/drafts/{draft_id}/prepare",
    response_model=BrowserAssistanceRead,
)
def prepare(
    draft_id: int,
    db: Session = Depends(get_db),
) -> dict:
    try:
        return prepare_browser_assistance(db, draft_id=draft_id)
    except BrowserAssistanceError as error:
        raise HTTPException(
            status_code=error.status_code, detail=error.message
        ) from error
