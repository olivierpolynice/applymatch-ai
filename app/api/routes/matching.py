from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.candidate_profiles import (
    get_profile_or_404,
)
from app.api.routes.job_offers import (
    get_offer_or_404,
)
from app.db.session import get_db
from app.models import MatchResult
from app.schemas import MatchResultRead
from app.services.match_results import (
    save_match_result,
)


router = APIRouter(
    prefix="/matching",
    tags=["Matching"],
)


def serialize_match(
    result: MatchResult,
) -> dict[str, Any]:
    decision = (
        "documents_ready"
        if result.decision == "automatic_ready"
        else result.decision
    )

    return {
        "id": result.id,
        "profile_id": result.profile_id,
        "offer_id": result.offer_id,
        "score": result.score,
        "recommendation": result.recommendation,
        "confidence": result.confidence,
        "decision": decision,
        "application_priority": (
            result.application_priority
        ),
        "actions": result.actions,
        "matched_skills": result.matched_skills,
        "skills_to_strengthen": (
            result.skills_to_strengthen
        ),
        "missing_skills": result.missing_skills,
        "known_technologies": (
            result.known_technologies
        ),
        "unknown_technologies": (
            result.unknown_technologies
        ),
        "required_technologies": (
            result.required_technologies
        ),
        "preferred_technologies": (
            result.preferred_technologies
        ),
        "explanation": {
            "total_score": result.score,
            "known_skills": result.known_technologies,
            "unknown_skills": result.unknown_technologies,
            "blocking_reasons": result.eligibility_reasons,
            "decision": decision,
        },
        "details": {
            "skills_score": result.skills_score,
            "role_score": result.role_score,
            "contract_score": (
                result.contract_score
            ),
            "location_score": (
                result.location_score
            ),
            "education_score": (
                result.education_score
            ),
            "experience_score": (
                result.experience_score
            ),
            "freshness_score": (
                result.freshness_score
            ),
            "role_match": result.role_match,
            "contract_match": (
                result.contract_match
            ),
            "location_match": (
                result.location_match
            ),
            "education_match": (
                result.education_match
            ),
            "experience_match": (
                result.experience_match
            ),
            "eligibility_reasons": (
                result.eligibility_reasons
            ),
        },
        "created_at": result.created_at,
        "updated_at": result.updated_at,
    }


@router.post(
    "/profile/{profile_id}/offer/{offer_id}",
    response_model=MatchResultRead,
)
def match_profile_offer(
    profile_id: int,
    offer_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    profile = get_profile_or_404(
        profile_id,
        db,
    )
    offer = get_offer_or_404(
        offer_id,
        db,
    )

    result = save_match_result(
        db,
        profile=profile,
        offer=offer,
    )

    return serialize_match(result)


@router.get(
    "/profile/{profile_id}/results",
    response_model=list[MatchResultRead],
)
def list_match_results(
    profile_id: int,
    minimum_score: int = 0,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    get_profile_or_404(
        profile_id,
        db,
    )

    if not 0 <= minimum_score <= 100:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            detail=(
                "minimum_score must be "
                "between 0 and 100"
            ),
        )

    statement = (
        select(MatchResult)
        .where(
            MatchResult.profile_id == profile_id,
            MatchResult.score >= minimum_score,
        )
        .order_by(
            MatchResult.score.desc(),
        )
    )

    results = db.scalars(statement)

    return [
        serialize_match(result)
        for result in results
    ]
