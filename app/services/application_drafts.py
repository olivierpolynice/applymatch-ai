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


class ApplicationDraftError(RuntimeError):
    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_skills(skills: list[str]) -> str:
    if not skills:
        return "mes compétences techniques"
    return ", ".join(skills)


def get_draft_or_error(db: Session, draft_id: int) -> ApplicationDraft:
    draft = db.get(ApplicationDraft, draft_id)
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
    item = db.get(ValidationQueueItem, queue_item_id)
    if item is None:
        raise ApplicationDraftError(
            "Validation queue item not found",
            status_code=404,
        )
    if item.status != "approved":
        raise ApplicationDraftError(
            (
                "The application must be manually approved "
                "before generating documents"
            ),
            status_code=422,
        )
    return item


def load_generation_context(
    db: Session,
    item: ValidationQueueItem,
) -> tuple[CandidateProfile, JobOffer, MatchResult]:
    profile = db.get(CandidateProfile, item.profile_id)
    offer = db.get(JobOffer, item.offer_id)
    match_result = db.get(MatchResult, item.match_result_id)
    if profile is None or offer is None or match_result is None:
        raise ApplicationDraftError(
            "Application generation context is incomplete",
            status_code=409,
        )
    return profile, offer, match_result


def build_cover_letter(
    profile: CandidateProfile,
    offer: JobOffer,
    match_result: MatchResult,
) -> str:
    matched_skills = format_skills(match_result.matched_skills)
    professional_summary = profile.professional_summary or (
        f"Actuellement en {profile.education_level}, "
        f"je suis le programme {profile.program}."
    )

    experience_paragraph = ""
    if profile.experience_highlights:
        experience_paragraph = (
            "\n\nMon parcours m’a notamment permis de développer "
            "les expériences suivantes : "
            f"{profile.experience_highlights}"
        )

    project_paragraph = ""
    if profile.project_highlights:
        project_paragraph = (
            "\n\nMes projets m’ont également permis de mettre "
            "en pratique ces compétences : "
            f"{profile.project_highlights}"
        )

    return (
        f"Objet : Candidature – {offer.title}\n\n"
        "Madame, Monsieur,\n\n"
        f"Je souhaite vous proposer ma candidature au poste de "
        f"{offer.title} au sein de {offer.company}. "
        f"{professional_summary}\n\n"
        "Cette opportunité correspond à mon projet professionnel "
        f"dans les domaines suivants : {profile.target_roles}. "
        "Mon profil présente plusieurs compétences en adéquation "
        f"avec l’offre, notamment {matched_skills}."
        f"{experience_paragraph}"
        f"{project_paragraph}\n\n"
        f"Disponible {profile.availability}, selon un rythme de "
        f"{profile.work_schedule}, je serais heureux d’échanger "
        "avec vous afin de vous présenter plus précisément ma "
        "motivation et mon parcours.\n\n"
        "Je vous prie d’agréer, Madame, Monsieur, l’expression "
        "de mes salutations distinguées.\n\n"
        f"{profile.full_name}"
    )


def build_short_message(
    profile: CandidateProfile,
    offer: JobOffer,
    match_result: MatchResult,
) -> str:
    highlighted_skills = format_skills(match_result.matched_skills[:4])
    return (
        f"Bonjour, je souhaite candidater à votre offre "
        f"« {offer.title} » chez {offer.company}. "
        f"Actuellement en {profile.education_level} – "
        f"{profile.program}, je recherche {profile.target_contract} "
        f"à partir de {profile.availability}. Mes compétences en "
        f"{highlighted_skills} correspondent aux missions "
        "proposées. Je serais ravi d’échanger avec vous. "
        f"Cordialement, {profile.full_name}."
    )


def build_cv_adaptation_tips(
    profile: CandidateProfile,
    offer: JobOffer,
    match_result: MatchResult,
) -> str:
    tips = [f"Adapter le titre du CV à l’offre : « {offer.title} »." ]

    if match_result.matched_skills:
        skills = format_skills(match_result.matched_skills)
        tips.append(f"Mettre en avant les compétences suivantes : {skills}.")

    if match_result.skills_to_strengthen:
        skills = format_skills(match_result.skills_to_strengthen)
        tips.append(f"Présenter honnêtement comme notions : {skills}.")

    if match_result.missing_skills:
        skills = format_skills(match_result.missing_skills)
        tips.append(
            "Ne pas revendiquer sans preuve les compétences "
            f"suivantes : {skills}."
        )

    if profile.project_highlights:
        tips.append(
            "Sélectionner les projets les plus proches des "
            f"missions proposées par {offer.company}."
        )

    tips.append(
        "Conserver uniquement des informations vérifiables et "
        "ne jamais inventer une expérience."
    )
    return "\n".join(f"- {tip}" for tip in tips)


def create_application_draft(
    db: Session,
    validation_queue_item_id: int,
) -> ApplicationDraft:
    item = get_approved_queue_item(db, validation_queue_item_id)
    existing_draft = db.scalar(
        select(ApplicationDraft).where(
            ApplicationDraft.validation_queue_item_id == item.id
        )
    )
    if existing_draft is not None:
        raise ApplicationDraftError(
            "An application draft already exists for this validation",
            status_code=409,
        )

    profile, offer, match_result = load_generation_context(db, item)
    draft = ApplicationDraft(
        validation_queue_item_id=item.id,
        profile_id=profile.id,
        offer_id=offer.id,
        status="draft",
        version=1,
        cover_letter=build_cover_letter(profile, offer, match_result),
        short_message=build_short_message(profile, offer, match_result),
        cv_adaptation_tips=build_cv_adaptation_tips(
            profile,
            offer,
            match_result,
        ),
        generated_at=utc_now(),
    )
    db.add(draft)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ApplicationDraftError(
            "An application draft already exists for this validation",
            status_code=409,
        ) from error
    db.refresh(draft)
    return draft


def update_application_draft(
    db: Session,
    draft_id: int,
    update_data: dict[str, object],
) -> ApplicationDraft:
    draft = get_draft_or_error(db, draft_id)
    for key, value in update_data.items():
        setattr(draft, key, value)
    db.commit()
    db.refresh(draft)
    return draft


def regenerate_application_draft(
    db: Session,
    draft_id: int,
) -> ApplicationDraft:
    draft = get_draft_or_error(db, draft_id)
    item = get_approved_queue_item(db, draft.validation_queue_item_id)
    profile, offer, match_result = load_generation_context(db, item)
    draft.cover_letter = build_cover_letter(profile, offer, match_result)
    draft.short_message = build_short_message(profile, offer, match_result)
    draft.cv_adaptation_tips = build_cv_adaptation_tips(
        profile,
        offer,
        match_result,
    )
    draft.status = "draft"
    draft.version += 1
    draft.generated_at = utc_now()
    db.commit()
    db.refresh(draft)
    return draft