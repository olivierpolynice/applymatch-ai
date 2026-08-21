from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth_dependencies import (
    get_current_admin,
)
from app.db.session import get_db
from app.models import AdminUser, ApplicationDraft, JobOffer
from app.schemas import (
    JobOfferCreate,
    JobOfferRead,
    JobOfferUpdate,
)
from app.services.job_offers import (
    DuplicateJobOfferError,
    create_job_offer as create_job_offer_service,
)
from app.services.application_automation import (
    archive_confirmed_application,
)


router = APIRouter(
    prefix="/job-offers",
    tags=["Job offers"],
)


def get_offer_or_404(
    offer_id: int,
    db: Session,
) -> JobOffer:
    offer = db.get(JobOffer, offer_id)

    if offer is None:
        raise HTTPException(
            status_code=404,
            detail="Job offer not found",
        )

    return offer


@router.post(
    "",
    response_model=JobOfferRead,
    status_code=201,
)
def create_job_offer(
    data: JobOfferCreate,
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(
        get_current_admin,
    ),
) -> JobOffer:
    try:
        return create_job_offer_service(
            db=db,
            data=data,
        )
    except DuplicateJobOfferError as error:
        raise HTTPException(
            status_code=409,
            detail=error.message,
        ) from error


@router.get(
    "",
    response_model=list[JobOfferRead],
)
def list_job_offers(
    status_filter: str | None = Query(
        default=None,
        alias="status",
    ),
    db: Session = Depends(get_db),
) -> list[JobOffer]:
    statement = select(JobOffer).order_by(
        JobOffer.created_at.desc(),
    )

    if status_filter is not None:
        statement = statement.where(
            JobOffer.status == status_filter,
        )

    return list(db.scalars(statement))


@router.get(
    "/{offer_id}",
    response_model=JobOfferRead,
)
def get_job_offer(
    offer_id: int,
    db: Session = Depends(get_db),
) -> JobOffer:
    return get_offer_or_404(
        offer_id,
        db,
    )


@router.patch(
    "/{offer_id}",
    response_model=JobOfferRead,
)
def update_job_offer(
    offer_id: int,
    data: JobOfferUpdate,
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(
        get_current_admin,
    ),
) -> JobOffer:
    offer = get_offer_or_404(
        offer_id,
        db,
    )
    update_data = data.model_dump(
        exclude_unset=True,
    )

    new_status = update_data.get("status")

    if new_status == "applied" and offer.status != "applied":
        offer.applied_at = datetime.now(timezone.utc)
    elif new_status is not None and new_status != "applied":
        offer.applied_at = None

    for key, value in update_data.items():
        setattr(offer, key, value)

    db.commit()
    db.refresh(offer)

    return offer


@router.post(
    "/{offer_id}/mark-applied",
    response_model=JobOfferRead,
)
def mark_job_offer_as_applied(
    offer_id: int,
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(
        get_current_admin,
    ),
) -> JobOffer:
    offer = get_offer_or_404(
        offer_id,
        db,
    )

    if offer.status == "applied":
        raise HTTPException(
            status_code=409,
            detail="Job offer is already marked as applied",
        )

    draft = db.scalar(
        select(ApplicationDraft)
        .where(ApplicationDraft.offer_id == offer.id)
        .order_by(ApplicationDraft.updated_at.desc())
    )

    if draft is not None:
        archive_confirmed_application(
            db,
            draft_id=draft.id,
            channel="unsupported",
            channel_authorized=False,
            has_unknown_questions=False,
            provider_confirmation_id=(
                f"manual-{offer.id}-"
                f"{datetime.now(timezone.utc).isoformat()}"
            ),
            application_mode="manual",
        )
        db.refresh(offer)
        return offer

    offer.status = "applied"
    offer.applied_at = datetime.now(timezone.utc)
    offer.application_channel = "manual"
    offer.application_status = "sent"
    offer.provider_confirmation_id = (
        f"manual-{offer.id}-{offer.applied_at.isoformat()}"
    )

    db.commit()
    db.refresh(offer)

    return offer


@router.delete(
    "/{offer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_job_offer(
    offer_id: int,
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(
        get_current_admin,
    ),
) -> None:
    offer = get_offer_or_404(
        offer_id,
        db,
    )

    db.delete(offer)
    db.commit()
