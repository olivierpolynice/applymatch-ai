import logging
import re
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
from app.services.technology_matcher import (
    normalize,
    verified_catalog,
)


logger = logging.getLogger(__name__)

FRENCH_MONTHS = {
    1: "janvier",
    2: "février",
    3: "mars",
    4: "avril",
    5: "mai",
    6: "juin",
    7: "juillet",
    8: "août",
    9: "septembre",
    10: "octobre",
    11: "novembre",
    12: "décembre",
}


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


def verified_skills_for_draft(
    match_result: MatchResult,
) -> list[str]:
    """Return only canonical technologies backed by profile evidence."""
    if match_result.known_technologies:
        return list(match_result.known_technologies)

    aliases_to_name = {
        normalize(alias): technology.name
        for technology in verified_catalog()
        for alias in [technology.name, *technology.aliases]
    }

    return list(
        dict.fromkeys(
            aliases_to_name[normalize(skill)]
            for skill in match_result.matched_skills
            if normalize(skill) in aliases_to_name
        )
    )


def format_availability(value: str) -> str:
    normalized_value = value.strip()
    match = re.fullmatch(
        r"(\d{4})-(\d{2})",
        normalized_value,
    )

    if match is None:
        return normalized_value

    year = match.group(1)
    month = int(match.group(2))
    month_name = FRENCH_MONTHS.get(month)

    if month_name is None:
        return normalized_value

    return f"{month_name} {year}"


def format_contract(value: str) -> str:
    normalized_value = value.strip().casefold()

    if normalized_value == "alternance":
        return "une alternance"

    if normalized_value == "apprentissage":
        return "un contrat d’apprentissage"

    if normalized_value.startswith(("un ", "une ")):
        return value.strip()

    return value.strip()


def join_french(items: list[str]) -> str:
    if not items:
        return "les métiers du numérique"

    if len(items) == 1:
        return items[0]

    if len(items) == 2:
        return f"{items[0]} et {items[1]}"

    return (
        ", ".join(items[:-1])
        + f" ainsi que {items[-1]}"
    )


def format_target_domains(value: str) -> str:
    normalized_value = value.casefold()
    domains: list[str] = []

    candidates = (
        (
            "la cybersécurité",
            ("cybersécurité", "cybersecurite", "cyber"),
        ),
        ("le cloud", ("cloud",)),
        ("le DevSecOps", ("devsecops",)),
        (
            "les systèmes et réseaux",
            ("système", "systeme", "réseau", "reseau", "network"),
        ),
        (
            "l’intelligence artificielle",
            ("intelligence artificielle", "artificial intelligence"),
        ),
    )

    for label, keywords in candidates:
        if any(
            keyword in normalized_value
            for keyword in keywords
        ):
            domains.append(label)

    return join_french(domains)


def build_ai_experience_paragraph() -> str:
    return (
        "J’ai également acquis une expérience pratique "
        "en intelligence artificielle en concevant "
        "ApplyMatch AI, un assistant qui automatise la "
        "collecte et le rapprochement d’offres, le "
        "scoring et la préparation contrôlée de "
        "brouillons, tout en maintenant une validation "
        "humaine avant toute candidature."
    )


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
    verified_skills = verified_skills_for_draft(match_result)
    matched_skills = format_skills(
        verified_skills
    )
    availability = format_availability(
        profile.availability
    )
    target_domains = format_target_domains(
        profile.target_roles
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
            "de développer des compétences concrètes : "
            f"{profile.experience_highlights}"
        )

    project_paragraph = ""

    if profile.project_highlights:
        project_paragraph = (
            "\n\nMes projets m’ont permis de mettre "
            "ces compétences en pratique, notamment : "
            f"{profile.project_highlights}"
        )

    ai_experience_paragraph = (
        "\n\n"
        + build_ai_experience_paragraph()
    )

    return (
        f"Objet : Candidature – {offer.title}\n\n"
        "Madame, Monsieur,\n\n"
        "Je souhaite vous proposer ma candidature "
        f"au poste de {offer.title} au sein de "
        f"{offer.company}. {professional_summary}\n\n"
        "Cette opportunité s’inscrit pleinement dans "
        "mon projet professionnel, orienté vers "
        f"{target_domains}. Les compétences détectées "
        "comme directement pertinentes pour cette "
        f"offre sont notamment {matched_skills}."
        f"{experience_paragraph}"
        f"{project_paragraph}"
        f"{ai_experience_paragraph}\n\n"
        f"Disponible à partir de {availability}, selon "
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
    verified_skills = verified_skills_for_draft(match_result)
    highlighted_skills = format_skills(
        verified_skills[:4]
    )
    availability = format_availability(
        profile.availability
    )
    contract = format_contract(
        profile.target_contract
    )

    return (
        "Bonjour, je souhaite candidater à votre "
        f"offre « {offer.title} » chez "
        f"{offer.company}. Actuellement en "
        f"{profile.education_level} – "
        f"{profile.program}, je recherche "
        f"{contract} à partir de {availability}. "
        "J’ai développé une expérience pratique en IA "
        "en concevant ApplyMatch AI. Mes compétences "
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
            "Valoriser l’expérience pratique en IA "
            "acquise avec ApplyMatch AI, en précisant "
            "les fonctionnalités réellement développées."
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


def build_adapted_cv_snapshot(
    profile: CandidateProfile,
    offer: JobOffer,
    match_result: MatchResult,
) -> str:
    """Build a truthful, text-only CV version suitable for archiving."""
    verified_skills = verified_skills_for_draft(match_result)
    matched = format_skills(verified_skills)
    return (
        f"{profile.full_name}\n"
        f"POSTE CIBLÉ : {offer.title}\n\n"
        f"PROFIL\n{profile.professional_summary or profile.program}\n\n"
        f"FORMATION\n{profile.education_level} – {profile.program}\n\n"
        f"COMPÉTENCES PERTINENTES\n{matched}\n\n"
        f"EXPÉRIENCES\n{profile.experience_highlights or 'À compléter'}\n\n"
        f"PROJETS\n{profile.project_highlights or 'À compléter'}\n\n"
        f"DISPONIBILITÉ\n{profile.availability} – {profile.work_schedule}\n"
        f"LOCALISATION\n{profile.location}"
    )


def build_proposed_answers(
    profile: CandidateProfile,
) -> list[dict[str, str]]:
    return [
        {"question": "Quand êtes-vous disponible ?", "answer": profile.availability},
        {"question": "Quel rythme recherchez-vous ?", "answer": profile.work_schedule},
        {"question": "Quel contrat recherchez-vous ?", "answer": profile.target_contract},
    ]


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
        adapted_cv_snapshot=build_adapted_cv_snapshot(
            profile, offer, match_result
        ),
        proposed_answers=build_proposed_answers(profile),
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
    draft.adapted_cv_snapshot = build_adapted_cv_snapshot(
        profile, offer, match_result
    )
    draft.proposed_answers = build_proposed_answers(profile)
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
