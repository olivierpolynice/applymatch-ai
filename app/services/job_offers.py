import hashlib
import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import JobOffer
from app.schemas import JobOfferCreate


DUPLICATE_URL_MESSAGE = (
    "A job offer with this source URL already exists"
)
DUPLICATE_OFFER_MESSAGE = "This job offer already exists"
DUPLICATE_EXTERNAL_ID_MESSAGE = (
    "A job offer with this source and external ID already exists"
)


class DuplicateJobOfferError(RuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def normalize_fingerprint_value(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized.strip().casefold()


def build_offer_fingerprint(
    title: str,
    company: str,
    location: str,
    source: str = "",
    external_id: str | None = None,
    source_url: str | None = None,
) -> str:
    if external_id:
        normalized_values = [
            normalize_fingerprint_value(source),
            normalize_fingerprint_value(external_id),
        ]
    else:
        normalized_values = [
            normalize_fingerprint_value(company),
            normalize_fingerprint_value(title),
            normalize_fingerprint_value(location),
            normalize_fingerprint_value(source_url or ""),
        ]
    fingerprint_source = "|".join(normalized_values)

    return hashlib.sha256(
        fingerprint_source.encode("utf-8"),
    ).hexdigest()


def create_job_offer(
    db: Session,
    data: JobOfferCreate,
) -> JobOffer:
    offer_data = data.model_dump()
    source_url = offer_data.get("source_url")
    external_id = offer_data.get("external_id")

    if external_id is not None:
        existing_external_id = db.scalar(
            select(JobOffer).where(
                JobOffer.source == offer_data["source"],
                JobOffer.external_id == external_id,
            )
        )

        if existing_external_id is not None:
            raise DuplicateJobOfferError(
                DUPLICATE_EXTERNAL_ID_MESSAGE
            )

    if source_url is not None:
        source_url = str(source_url)
        offer_data["source_url"] = source_url

        existing_url = db.scalar(
            select(JobOffer).where(
                JobOffer.source_url == source_url,
            )
        )

        if existing_url is not None:
            raise DuplicateJobOfferError(
                DUPLICATE_URL_MESSAGE
            )

    fingerprint = build_offer_fingerprint(
        title=offer_data["title"],
        company=offer_data["company"],
        location=offer_data["location"],
        source=offer_data["source"],
        external_id=external_id,
        source_url=source_url,
    )

    existing_fingerprint = db.scalar(
        select(JobOffer).where(
            JobOffer.fingerprint == fingerprint,
        )
    )

    if existing_fingerprint is not None:
        raise DuplicateJobOfferError(
            DUPLICATE_OFFER_MESSAGE
        )

    offer_data["fingerprint"] = fingerprint

    offer = JobOffer(**offer_data)
    db.add(offer)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()

        raise DuplicateJobOfferError(
            DUPLICATE_OFFER_MESSAGE
        ) from error

    db.refresh(offer)

    return offer
