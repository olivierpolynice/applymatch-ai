import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    ApplicationDraft,
    CandidateProfile,
    JobOffer,
    MatchResult,
    ValidationQueueItem,
)
from app.services.notifications import (
    create_notification_once,
)


logger = logging.getLogger(__name__)


class ApplicationDraftError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_skills(
    skills: list[str],
) -> str:
    if not skills:
        return "mes compétences techniques"

    return ", ".join(skills)


def get_draft_or_error(
    db: Session,
    draft_id: int,
) -> ApplicationDraft:
    draft = db.get(
        ApplicationDraft,
        draft_id,
    )

    if draft is None:
        raise ApplicationDraftError(
            "Application draft not found",
            status_code=404,
        )

    return draft


def get_approved_queue_item(
    db: Session,
    queue_item_id: int,
) -> ValidationQueueItem:
    item = db.get(
        ValidationQueueItem,
        queue_item_id,
    )

    if item is None:
        raise ApplicationDraftError(
            "Validation queue item not found",
            status_code=404,
        )

    if item.status != "approved":
        raise ApplicationDraftError(
            (
                "The application must be manually "
                "approved before generating documents"
            ),
            status_code=422,
        )

    return item


def load_generation_context(
    db: Session,
    item: ValidationQueueItem,
) -> tuple[
    CandidateProfile,
    JobOffer,
    MatchResult,
]:
    profile = db.get(
        CandidateProfile,
        item.profile_id,
    )
    offer = db.get(
        JobOffer,
        item.offer_id,
    )
    match_result = db.get(
        MatchResult,
        item.match_result_id,
    )

    if (
        profile is None
        or offer is None
        or match_result is None
    ):
        raise ApplicationDraftError(
            (
                "Application generation context "
                "is incomplete"
            ),
            status_code=409,
        )

    return profile, offer, match_result


def build_cover_letter(
    profile: CandidateProfile,
    offer: JobOffer,
    match_result: MatchResult,
) -> str:
    matched_skills = format_skills(
        match_result.matched_skills
    )
    professional_summary = (
        profile.professional_summary
        or (
            f"Actuellement en "
            f"{profile.education_level}, "
            f"je suis le programme "
            f"{profile.program}."
        )
    )

    experience_paragraph = ""

    if profile.experience_highlights:
        experience_paragraph = (
            "\n\nMon parcours m’a notamment permis "
            "de développer les expériences suivantes : "
            f"{profile.experience_highlights}"
        )

    project_paragraph = ""

    if profile.project_highlights:
        project_paragraph = (
            "\n\nMes projets m’ont également permis "
            "de mettre en pratique ces compétences : "
            f"{profile.project_highlights}"
        )

    return (
        f"Objet : Candidature – {offer.title}\n\n"
        "Madame, Monsieur,\n\n"
        "Je souhaite vous proposer ma candidature "
        f"au poste de {offer.title} au sein de "
        f"{offer.company}. {professional_summary}\n\n"
        "Cette opportunité correspond à mon projet "
        "professionnel dans les domaines suivants : "
        f"{profile.target_roles}. Mon profil présente "
        "plusieurs compétences en adéquation avec "
        f"l’offre, notamment {matched_skills}."
        f"{experience_paragraph}"
        f"{project_paragraph}\n\n"
        f"Disponible {profile.availability}, selon "
        f"un rythme de {profile.work_schedule}, "
        "je serais heureux d’échanger avec vous afin "
        "de vous présenter plus précisément ma "
        "motivation et mon parcours.\n\n"
        "Je vous prie d’agréer, Madame, Monsieur, "
        "l’expression de mes salutations "
        "distinguées.\n\n"
        f"{profile.full_name}"
    )


def build_short_message(
    profile: CandidateProfile,
    offer: JobOffer,
    match_result: MatchResult,
) -> str:
    highlighted_skills = format_skills(
        match_result.matched_skills[:4]
    )

    return (
        "Bonjour, je souhaite candidater à votre "
        f"offre « {offer.title} » chez "
        f"{offer.company}. Actuellement en "
        f"{profile.education_level} – "
        f"{profile.program}, je recherche "
        f"{profile.target_contract} à partir de "
        f"{profile.availability}. Mes compétences "
        f"en {highlighted_skills} correspondent "
        "aux missions proposées. Je serais ravi "
        "d’échanger avec vous. Cordialement, "
        f"{profile.full_name}."
    )


def build_cv_adaptation_tips(
    profile: CandidateProfile,
    offer: JobOffer,
    match_result: MatchResult,
) -> str:
    tips = [
        (
            "Adapter le titre du CV à l’offre : "
            f"« {offer.title} »."
        )
    ]

    if match_result.matched_skills:
        skills = format_skills(
            match_result.matched_skills
        )
        tips.append(
            (
                "Mettre en avant les compétences "
                f"suivantes : {skills}."
            )
        )

    if match_result.skills_to_strengthen:
        skills = format_skills(
            match_result.skills_to_strengthen
        )
        tips.append(
            (
                "Présenter honnêtement comme notions : "
                f"{skills}."
            )
        )

    if match_result.missing_skills:
        skills = format_skills(
            match_result.missing_skills
        )
        tips.append(
            (
                "Ne pas revendiquer sans preuve les "
                f"compétences suivantes : {skills}."
            )
        )

    if profile.project_highlights:
        tips.append(
            (
                "Sélectionner les projets les plus "
                "proches des missions proposées par "
                f"{offer.company}."
            )
        )

    tips.append(
        (
            "Conserver uniquement des informations "
            "vérifiables et ne jamais inventer "
            "une expérience."
        )
    )

    return "\n".join(
        f"- {tip}"
        for tip in tips
    )


def create_draft_notification(
    db: Session,
    *,
    draft: ApplicationDraft,
    offer: JobOffer,
) -> None:
    try:
        create_notification_once(
            db,
            notification_type="draft_ready",
            level="success",
            title=(
                f"Brouillon prêt : {offer.title}"
            )[:200],
            message=(
                f"Les documents de candidature pour "
                f"{offer.company} sont prêts. "
                f"Version {draft.version} à vérifier "
                "avant toute utilisation."
            ),
            target_url=(
                f"#draft-{draft.id}-"
                f"version-{draft.version}"
            ),
        )
    except Exception:
        db.rollback()

        logger.exception(
            (
                "Unable to create draft-ready "
                "notification for draft %s "
                "version %s."
            ),
            draft.id,
            draft.version,
        )


def create_application_draft(
    db: Session,
    validation_queue_item_id: int,
) -> ApplicationDraft:
    item = get_approved_queue_item(
        db,
        validation_queue_item_id,
    )

    existing_draft = db.scalar(
        select(ApplicationDraft).where(
            ApplicationDraft
            .validation_queue_item_id
            == item.id
        )
    )

    if existing_draft is not None:
        raise ApplicationDraftError(
            (
                "An application draft already "
                "exists for this validation"
            ),
            status_code=409,
        )

    profile, offer, match_result = (
        load_generation_context(
            db,
            item,
        )
    )

    draft = ApplicationDraft(
        validation_queue_item_id=item.id,
        profile_id=profile.id,
        offer_id=offer.id,
        status="draft",
        version=1,
        cover_letter=build_cover_letter(
            profile,
            offer,
            match_result,
        ),
        short_message=build_short_message(
            profile,
            offer,
            match_result,
        ),
        cv_adaptation_tips=(
            build_cv_adaptation_tips(
                profile,
                offer,
                match_result,
            )
        ),
        generated_at=utc_now(),
    )

    db.add(draft)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()

        raise ApplicationDraftError(
            (
                "An application draft already "
                "exists for this validation"
            ),
            status_code=409,
        ) from error

    db.refresh(draft)

    create_draft_notification(
        db,
        draft=draft,
        offer=offer,
    )

    return draft


def update_application_draft(
    db: Session,
    draft_id: int,
    update_data: dict[str, object],
) -> ApplicationDraft:
    draft = get_draft_or_error(
        db,
        draft_id,
    )

    for key, value in update_data.items():
        setattr(
            draft,
            key,
            value,
        )

    db.commit()
    db.refresh(draft)

    return draft


def regenerate_application_draft(
    db: Session,
    draft_id: int,
) -> ApplicationDraft:
    draft = get_draft_or_error(
        db,
        draft_id,
    )
    item = get_approved_queue_item(
        db,
        draft.validation_queue_item_id,
    )
    profile, offer, match_result = (
        load_generation_context(
            db,
            item,
        )
    )

    draft.cover_letter = build_cover_letter(
        profile,
        offer,
        match_result,
    )
    draft.short_message = build_short_message(
        profile,
        offer,
        match_result,
    )
    draft.cv_adaptation_tips = (
        build_cv_adaptation_tips(
            profile,
            offer,
            match_result,
        )
    )
    draft.status = "draft"
    draft.version += 1
    draft.generated_at = utc_now()

    db.commit()
    db.refresh(draft)

    create_draft_notification(
        db,
        draft=draft,
        offer=offer,
    )

    return draft