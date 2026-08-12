from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import CandidateProfile
from app.schemas import (
    CandidateProfileCreate,
    CandidateProfileRead,
    CandidateProfileUpdate,
)
from app.services.profile_loader import sync_profile


router = APIRouter(
    prefix="/candidate-profiles",
    tags=["Candidate profiles"],
)


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


@router.post(
    "/sync",
    response_model=CandidateProfileRead,
)
def sync_candidate_profile(
    db: Session = Depends(get_db),
) -> CandidateProfile:
    return sync_profile(db)


@router.get(
    "",
    response_model=list[CandidateProfileRead],
)
def list_candidate_profiles(
    db: Session = Depends(get_db),
) -> list[CandidateProfile]:
    statement = select(CandidateProfile).order_by(
        CandidateProfile.id,
    )

    return list(db.scalars(statement))


@router.post(
    "",
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


@router.get(
    "/{profile_id}",
    response_model=CandidateProfileRead,
)
def get_candidate_profile(
    profile_id: int,
    db: Session = Depends(get_db),
) -> CandidateProfile:
    return get_profile_or_404(profile_id, db)


@router.patch(
    "/{profile_id}",
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