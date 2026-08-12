from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import SessionLocal, engine, get_db
from app.models import CandidateProfile, JobOffer, MatchResult
from app.schemas import (
    CandidateProfileCreate,
    CandidateProfileRead,
    CandidateProfileUpdate,
    JobOfferCreate,
    JobOfferRead,
    JobOfferUpdate,
)
from app.services.matching import calculate
from app.services.profile_loader import sync_profile


def serialize_match(result: MatchResult) -> dict[str, Any]:
    return {
        "id": result.id,
        "profile_id": result.profile_id,
        "offer_id": result.offer_id,
        "score": result.score,
        "recommendation": result.recommendation,
        "matched_skills": result.matched_skills,
        "missing_skills": result.missing_skills,
        "details": {
            "skills_score": result.skills_score,
            "role_score": result.role_score,
            "contract_score": result.contract_score,
            "location_score": result.location_score,
            "role_match": result.role_match,
            "contract_match": result.contract_match,
            "location_match": result.location_match,
        },
        "created_at": result.created_at,
        "updated_at": result.updated_at,
    }


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        sync_profile(db)

    yield


app = FastAPI(
    title="ApplyMatch AI API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/candidate-profiles/sync",
    response_model=CandidateProfileRead,
)
def sync_candidate_profile(
    db: Session = Depends(get_db),
) -> CandidateProfile:
    return sync_profile(db)


@app.get(
    "/candidate-profiles",
    response_model=list[CandidateProfileRead],
)
def list_candidate_profiles(
    db: Session = Depends(get_db),
) -> list[CandidateProfile]:
    statement = select(CandidateProfile).order_by(CandidateProfile.id)

    return list(db.scalars(statement))


@app.post(
    "/candidate-profiles",
    response_model=CandidateProfileRead,
    status_code=201,
)
def create_candidate_profile(
    data: CandidateProfileCreate,
    db: Session = Depends(get_db),
) -> CandidateProfile:
    profile = CandidateProfile(
        **data.model_dump(),
        is_active=True,
    )

    db.add(profile)
    db.commit()
    db.refresh(profile)

    return profile


def get_profile_or_404(
    profile_id: int,
    db: Session,
) -> CandidateProfile:
    profile = db.get(CandidateProfile, profile_id)

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Candidate profile not found",
        )

    return profile


@app.get(
    "/candidate-profiles/{profile_id}",
    response_model=CandidateProfileRead,
)
def get_candidate_profile(
    profile_id: int,
    db: Session = Depends(get_db),
) -> CandidateProfile:
    return get_profile_or_404(profile_id, db)


@app.patch(
    "/candidate-profiles/{profile_id}",
    response_model=CandidateProfileRead,
)
def update_candidate_profile(
    profile_id: int,
    data: CandidateProfileUpdate,
    db: Session = Depends(get_db),
) -> CandidateProfile:
    profile = get_profile_or_404(profile_id, db)

    update_data = data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)

    return profile


@app.post(
    "/job-offers",
    response_model=JobOfferRead,
    status_code=201,
)
def create_job_offer(
    data: JobOfferCreate,
    db: Session = Depends(get_db),
) -> JobOffer:
    offer_data = data.model_dump()

    if offer_data.get("source_url") is not None:
        offer_data["source_url"] = str(offer_data["source_url"])

    offer = JobOffer(**offer_data)
    db.add(offer)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="A job offer with this source URL already exists",
        ) from error

    db.refresh(offer)

    return offer


@app.get(
    "/job-offers",
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


@app.get(
    "/job-offers/{offer_id}",
    response_model=JobOfferRead,
)
def get_job_offer(
    offer_id: int,
    db: Session = Depends(get_db),
) -> JobOffer:
    return get_offer_or_404(offer_id, db)


@app.patch(
    "/job-offers/{offer_id}",
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


@app.post(
    "/matching/profile/{profile_id}/offer/{offer_id}",
)
def match_profile_offer(
    profile_id: int,
    offer_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    profile = get_profile_or_404(profile_id, db)
    offer = get_offer_or_404(offer_id, db)

    values = calculate(profile, offer)

    statement = select(MatchResult).where(
        MatchResult.profile_id == profile_id,
        MatchResult.offer_id == offer_id,
    )

    result = db.scalar(statement)

    if result is None:
        result = MatchResult(
            profile_id=profile_id,
            offer_id=offer_id,
            **values,
        )
        db.add(result)
    else:
        for key, value in values.items():
            setattr(result, key, value)

    db.commit()
    db.refresh(result)

    return serialize_match(result)


@app.get(
    "/matching/profile/{profile_id}/results",
)
def list_match_results(
    profile_id: int,
    minimum_score: int = 0,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    get_profile_or_404(profile_id, db)

    if not 0 <= minimum_score <= 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="minimum_score must be between 0 and 100",
        )

    statement = (
        select(MatchResult)
        .where(
            MatchResult.profile_id == profile_id,
            MatchResult.score >= minimum_score,
        )
        .order_by(MatchResult.score.desc())
    )

    results = db.scalars(statement)

    return [serialize_match(result) for result in results]