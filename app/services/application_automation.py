from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    ApplicationArchive,
    ApplicationDraft,
    JobOffer,
    MatchResult,
)
from app.models.application_archive import utc_now


AUTOMATIC_SCORE_THRESHOLD = 70
AUTHORIZED_CHANNELS = {
    "official_api",
    "recruitment_email",
    "authorized_form",
}
DUPLICATE_WINDOW_DAYS = 30


class ApplicationAutomationError(RuntimeError):
    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def load_context(
    db: Session, draft_id: int
) -> tuple[ApplicationDraft, JobOffer, MatchResult]:
    draft = db.get(ApplicationDraft, draft_id)
    if draft is None:
        raise ApplicationAutomationError(
            "Application draft not found", status_code=404
        )
    offer = db.get(JobOffer, draft.offer_id)
    match = db.scalar(
        select(MatchResult).where(
            MatchResult.profile_id == draft.profile_id,
            MatchResult.offer_id == draft.offer_id,
        )
    )
    if offer is None or match is None:
        raise ApplicationAutomationError(
            "Application context is incomplete", status_code=409
        )
    return draft, offer, match


def evaluate_automation(
    db: Session,
    *,
    draft_id: int,
    channel: str,
    channel_authorized: bool,
    has_unknown_questions: bool,
) -> dict[str, object]:
    draft, offer, match = load_context(db, draft_id)
    reasons: list[str] = []

    if match.score < AUTOMATIC_SCORE_THRESHOLD:
        reasons.append(f"Score inférieur à {AUTOMATIC_SCORE_THRESHOLD}/100")
    if not match.role_match:
        reasons.append("Métier non conforme")
    if not match.location_match:
        reasons.append("Localisation non conforme")
    if not match.contract_match:
        reasons.append("Contrat non conforme")
    if match.missing_skills:
        reasons.append("Compétences obligatoires manquantes ou non prouvées")
    if has_unknown_questions:
        reasons.append("Le formulaire contient une question inconnue")
    if channel not in AUTHORIZED_CHANNELS or not channel_authorized:
        reasons.append("Canal non autorisé ou non vérifié")
    if not draft.adapted_cv_snapshot.strip():
        reasons.append("CV adapté absent")

    cutoff = utc_now() - timedelta(days=DUPLICATE_WINDOW_DAYS)
    recent = db.scalar(
        select(ApplicationArchive).where(
            ApplicationArchive.company == offer.company,
            ApplicationArchive.sent_at >= cutoff,
        )
    )
    if recent is not None:
        reasons.append("Candidature récente déjà envoyée à cette entreprise")

    eligible = not reasons
    return {
        "mode": "automatic" if eligible else "manual_approval",
        "eligible": eligible,
        "reasons": reasons,
    }


def archive_confirmed_application(
    db: Session,
    *,
    draft_id: int,
    channel: str,
    channel_authorized: bool,
    has_unknown_questions: bool,
    provider_confirmation_id: str,
    application_mode: str,
) -> ApplicationArchive:
    draft, offer, _match = load_context(db, draft_id)

    if application_mode == "automatic":
        evaluation = evaluate_automation(
            db,
            draft_id=draft_id,
            channel=channel,
            channel_authorized=channel_authorized,
            has_unknown_questions=has_unknown_questions,
        )
        if not evaluation["eligible"]:
            raise ApplicationAutomationError(
                "Automatic application blocked: "
                + "; ".join(evaluation["reasons"]),
                status_code=422,
            )

    if not provider_confirmation_id.strip():
        raise ApplicationAutomationError(
            "A provider confirmation is required before archiving",
            status_code=422,
        )

    archive = ApplicationArchive(
        draft_id=draft.id,
        profile_id=draft.profile_id,
        offer_id=offer.id,
        company=offer.company,
        offer_title=offer.title,
        application_mode=application_mode,
        channel=channel,
        provider_confirmation_id=provider_confirmation_id.strip(),
        cv_snapshot=draft.adapted_cv_snapshot,
        cover_letter_snapshot=draft.cover_letter,
        short_message_snapshot=draft.short_message,
        proposed_answers_snapshot=draft.proposed_answers,
        sent_at=utc_now(),
    )
    offer.status = "applied"
    offer.applied_at = archive.sent_at
    draft.status = "archived"
    db.add(archive)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ApplicationAutomationError(
            "This application has already been archived",
            status_code=409,
        ) from error

    db.refresh(archive)
    return archive
