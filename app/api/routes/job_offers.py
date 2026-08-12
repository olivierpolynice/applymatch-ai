import hashlib
import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import JobOffer
from app.schemas import (
    JobOfferCreate,
    JobOfferRead,
    JobOfferUpdate,
)


router = APIRouter(
    prefix="/job-offers",
    tags=["Job offers"],
)


def normalize_fingerprint_value(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized.strip().casefold()


def build_offer_fingerprint(
    title: str,
    company: str,
    location: str,
) -> str:
    normalized_values = [
        normalize_fingerprint_value(title),
        normalize_fingerprint_value(company),
        normalize_fingerprint_value(location),
    ]
    fingerprint_source = "|".join(normalized_values)

    return hashlib.sha256(
        fingerprint_source.encode("utf-8"),
    ).hexdigest()


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
) -> JobOffer:
    offer_data = data.model_dump()

    source_url = offer_data.get("source_url")

    if source_url is not None:
        source_url = str(source_url)
        offer_data["source_url"] = source_url

        existing_url = db.scalar(
            select(JobOffer).where(
                JobOffer.source_url == source_url,
            )
        )

        if existing_url is not None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "A job offer with this source URL "
                    "already exists"
                ),
            )

    fingerprint = build_offer_fingerprint(
        title=offer_data["title"],
        company=offer_data["company"],
        location=offer_data["location"],
    )

    existing_fingerprint = db.scalar(
        select(JobOffer).where(
            JobOffer.fingerprint == fingerprint,
        )
    )

    if existing_fingerprint is not None:
        raise HTTPException(
            status_code=409,
            detail="This job offer already exists",
        )

    offer_data["fingerprint"] = fingerprint

    offer = JobOffer(**offer_data)
    db.add(offer)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="This job offer already exists",
        ) from error

    db.refresh(offer)

    return offer


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
    return get_offer_or_404(offer_id, db)


@router.patch(
    "/{offer_id}",
    response_model=JobOfferRead,
)
def update_job_offer(
    offer_id: int,
    data: JobOfferUpdate,
    db: Session = Depends(get_db),
) -> JobOffer:
    offer = get_offer_or_404(offer_id, db)
    update_data = data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(offer, key, value)

    db.commit()
    db.refresh(offer)

    return offer