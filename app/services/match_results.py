import logging
from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    CandidateProfile,
    JobOffer,
    MatchResult,
)
from app.services.matching import calculate
from app.services.notifications import (
    create_notification_once,
)


logger = logging.getLogger(__name__)

HIGH_SCORE_THRESHOLD = 70


@dataclass(frozen=True)
class AutomaticMatchingResult:
    analyzed: int
    skipped: int
    errors: int


def create_high_score_notification(
    db: Session,
    *,
    result: MatchResult,
    offer: JobOffer,
) -> None:
    if result.score < HIGH_SCORE_THRESHOLD:
        return

    try:
        create_notification_once(
            db,
            notification_type="high_score",
            level="success",
            title=(
                f"Offre compatible : {offer.title}"
            )[:200],
            message=(
                f"{offer.company} · Score de "
                f"compatibilité {result.score}/100. "
                "Une validation manuelle est "
                "recommandée."
            ),
            target_url=f"#match-{result.id}",
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


def save_match_result(
    db: Session,
    *,
    profile: CandidateProfile,
    offer: JobOffer,
) -> MatchResult:
    values = calculate(
        profile,
        offer,
    )

    result = db.scalar(
        select(MatchResult).where(
            MatchResult.profile_id == profile.id,
            MatchResult.offer_id == offer.id,
        )
    )

    if result is None:
        result = MatchResult(
            profile_id=profile.id,
            offer_id=offer.id,
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
        offer=offer,
    )

    return result


def get_active_profile(
    db: Session,
) -> CandidateProfile | None:
    return db.scalar(
        select(CandidateProfile)
        .where(
            CandidateProfile.is_active.is_(True),
        )
        .order_by(
            CandidateProfile.id.desc(),
        )
    )


def match_new_offers(
    db: Session,
    *,
    offer_ids: Iterable[int],
) -> AutomaticMatchingResult:
    profile = get_active_profile(db)

    if profile is None:
        logger.warning(
            (
                "Automatic matching skipped: "
                "no active candidate profile."
            )
        )

        return AutomaticMatchingResult(
            analyzed=0,
            skipped=0,
            errors=0,
        )

    analyzed = 0
    skipped = 0
    errors = 0

    for offer_id in dict.fromkeys(offer_ids):
        existing_result = db.scalar(
            select(MatchResult.id).where(
                MatchResult.profile_id == profile.id,
                MatchResult.offer_id == offer_id,
            )
        )

        if existing_result is not None:
            skipped += 1
            continue

        offer = db.get(
            JobOffer,
            offer_id,
        )

        if offer is None:
            errors += 1
            logger.error(
                (
                    "Automatic matching skipped "
                    "unknown offer %s."
                ),
                offer_id,
            )
            continue

        try:
            save_match_result(
                db,
                profile=profile,
                offer=offer,
            )
        except Exception:
            db.rollback()
            errors += 1

            logger.exception(
                (
                    "Automatic matching failed for "
                    "profile %s and offer %s."
                ),
                profile.id,
                offer_id,
            )
        else:
            analyzed += 1

    return AutomaticMatchingResult(
        analyzed=analyzed,
        skipped=skipped,
        errors=errors,
    )