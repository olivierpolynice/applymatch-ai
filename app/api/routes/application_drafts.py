from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth_dependencies import (
    get_current_admin,
)
from app.db.session import get_db
from app.models import (
    ApplicationDraft,
    CandidateProfile,
    JobOffer,
    MatchResult,
)
from app.schemas import (
    ApplicationDocumentsRead,
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
from app.services.document_generation import (
    draft_directory,
    generate_application_documents,
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


@router.post(
    "/{draft_id}/documents",
    response_model=ApplicationDocumentsRead,
)
def generate_documents(
    draft_id: int,
    db: Session = Depends(get_db),
) -> dict:
    draft = get_draft_or_error(db, draft_id)
    profile = db.get(CandidateProfile, draft.profile_id)
    offer = db.get(JobOffer, draft.offer_id)
    match_result = db.scalar(
        select(MatchResult).where(
            MatchResult.profile_id == draft.profile_id,
            MatchResult.offer_id == draft.offer_id,
        )
    )

    if profile is None or offer is None or match_result is None:
        raise HTTPException(
            status_code=409,
            detail="Document generation context is incomplete",
        )

    generated = generate_application_documents(
        draft=draft,
        profile=profile,
        offer=offer,
        match_result=match_result,
    )
    base_url = f"/application-drafts/{draft.id}/documents"
    return {
        "draft_id": draft.id,
        "version": draft.version,
        "cover_letter_docx_url": f"{base_url}/cover-letter-docx",
        "cover_letter_pdf_url": f"{base_url}/cover-letter-pdf",
        "adapted_cv_pdf_url": f"{base_url}/adapted-cv-pdf",
        "short_message": draft.short_message,
        "validation": {
            "valid": generated.validation.valid,
            "errors": generated.validation.errors,
        },
    }


@router.get("/{draft_id}/documents/{document_type}")
def download_document(
    draft_id: int,
    document_type: str,
    db: Session = Depends(get_db),
) -> FileResponse:
    draft = get_draft_or_error(db, draft_id)
    filenames = {
        "cover-letter-docx": (
            "lettre-motivation.docx",
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document",
        ),
        "cover-letter-pdf": (
            "lettre-motivation.pdf",
            "application/pdf",
        ),
        "adapted-cv-pdf": (
            "cv-adapte.pdf",
            "application/pdf",
        ),
    }

    if document_type not in filenames:
        raise HTTPException(status_code=404, detail="Unknown document")

    filename, media_type = filenames[document_type]
    path = draft_directory(draft) / filename

    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Generate the documents before downloading them",
        )

    return FileResponse(
        path,
        media_type=media_type,
        filename=filename,
    )
