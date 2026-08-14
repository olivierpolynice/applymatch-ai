import logging
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
from app.services.matching import calculate
from app.services.notifications import (
    create_notification_once,
)


logger = logging.getLogger(__name__)

HIGH_SCORE_THRESHOLD = 70


router = APIRouter(
    prefix="/matching",
    tags=["Matching"],
)


def serialize_match(
    result: MatchResult,
) -> dict[str, Any]:
    return {
        "id": result.id,
        "profile_id": result.profile_id,
        "offer_id": result.offer_id,
        "score": result.score,
        "recommendation": result.recommendation,
        "confidence": result.confidence,
        "decision": result.decision,
        "application_priority": (
            result.application_priority
        ),
        "actions": result.actions,
        "matched_skills": result.matched_skills,
        "skills_to_strengthen": (
            result.skills_to_strengthen
        ),
        "missing_skills": result.missing_skills,
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
        },
        "created_at": result.created_at,
        "updated_at": result.updated_at,
    }


def create_high_score_notification(
    db: Session,
    *,
    result: MatchResult,
    offer_title: str,
    company: str,
) -> None:
    if result.score < HIGH_SCORE_THRESHOLD:
        return

    try:
        create_notification_once(
            db,
            notification_type="high_score",
            level="success",
            title=(
                f"Offre compatible : {offer_title}"
            )[:200],
            message=(
                f"{company} · Score de compatibilité "
                f"{result.score}/100. Une validation "
                "manuelle est recommandée."
            ),
            target_url=(
                f"#match-{result.id}"
            ),
        )
    except Exception:
        db.rollback()

        logger.exception(
            (
                "Unable to create high-score "
                "notification for match %s."
            ),
            result.id,
        )


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

    values = calculate(
        profile,
        offer,
    )

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
            setattr(
                result,
                key,
                value,
            )

    db.commit()
    db.refresh(result)

    create_high_score_notification(
        db,
        result=result,
        offer_title=offer.title,
        company=offer.company,
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