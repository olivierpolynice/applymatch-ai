import re
import logging
import unicodedata
from datetime import datetime, timezone
from typing import Any

from app.models import CandidateProfile, JobOffer
from app.services.priority_filter import evaluate_priority_offer
from app.services.scoring_engine import explain_score
from app.services.technology_matcher import (
    analyze_technologies,
)
from app.observability import log_event


logger = logging.getLogger(__name__)


SKILLS: dict[str, tuple[str, ...]] = {
    "active directory": (
        "active directory",
        "entra id",
        "azure ad",
    ),
    "ansible": ("ansible",),
    "aws": (
        "aws",
        "amazon web services",
    ),
    "azure": ("azure",),
    "ci/cd": (
        "ci/cd",
        "cicd",
        "github actions",
        "gitlab ci",
        "jenkins",
    ),
    "cloud": ("cloud",),
    "data science": (
        "data science",
        "data scientist",
    ),
    "devops": ("devops",),
    "devsecops": ("devsecops",),
    "docker": ("docker",),
    "fastapi": ("fastapi",),
    "git": ("git", "github"),
    "gcp": (
        "gcp",
        "google cloud",
        "google cloud platform",
    ),
    "grafana": ("grafana",),
    "iam": (
        "iam",
        "identity and access management",
        "gestion des identites",
    ),
    "intelligence artificielle": (
        "intelligence artificielle",
        "artificial intelligence",
        "ingenieur ia",
        "ai engineer",
    ),
    "jwt": ("jwt",),
    "javascript": ("javascript", "node.js", "nodejs"),
    "kubernetes": (
        "kubernetes",
        "k8s",
    ),
    "linux": ("linux",),
    "llm": (
        "llm",
        "large language model",
        "modeles de langage",
    ),
    "machine learning": (
        "machine learning",
        "apprentissage automatique",
        "ml engineer",
    ),
    "mlops": ("mlops",),
    "networking": (
        "networking",
        "network",
        "reseau",
        "reseaux",
        "tcp/ip",
        "cisco",
    ),
    "pentest": (
        "pentest",
        "penetration testing",
        "test d intrusion",
        "tests d intrusion",
    ),
    "postgresql": (
        "postgresql",
        "postgres",
    ),
    "prometheus": ("prometheus",),
    "python": ("python",),
    "pytest": ("pytest",),
    "rbac": (
        "rbac",
        "role based access control",
    ),
    "react": ("react",),
    "next.js": ("next.js", "nextjs"),
    "sqlalchemy": ("sqlalchemy",),
    "alembic": ("alembic",),
    "sqlite": ("sqlite",),
    "api rest": ("api rest", "rest api", "restful"),
    "security": (
        "security",
        "securite",
        "cybersecurite",
        "cyber security",
        "securisation",
    ),
    "siem": (
        "siem",
        "splunk",
        "qradar",
        "sentinel",
    ),
    "soc": (
        "soc",
        "security operations center",
        "centre operationnel de securite",
    ),
    "sql": ("sql",),
    "terraform": ("terraform",),
    "typescript": ("typescript",),
    "zero trust": ("zero trust",),
}


BEGINNER_MARKERS = {
    "base",
    "bases",
    "debutant",
    "debutante",
    "initiation",
    "notion",
    "notions",
    "en apprentissage",
    "a renforcer",
}


ROLE_DOMAINS: dict[str, set[str]] = {
    "cybersecurity": {
        "security",
        "soc",
        "siem",
        "pentest",
        "iam",
        "zero trust",
    },
    "cloud": {
        "cloud",
        "aws",
        "azure",
        "gcp",
        "terraform",
    },
    "networking": {
        "networking",
        "linux",
        "active directory",
    },
    "devsecops": {
        "devsecops",
        "devops",
        "ci/cd",
        "docker",
        "kubernetes",
        "terraform",
    },
    "artificial intelligence": {
        "intelligence artificielle",
        "machine learning",
        "data science",
        "llm",
        "mlops",
        "python",
    },
}


ILE_DE_FRANCE_DEPARTMENTS = {
    "75",
    "77",
    "78",
    "91",
    "92",
    "93",
    "94",
    "95",
}


ILE_DE_FRANCE_NAMES = {
    "paris",
    "seine et marne",
    "yvelines",
    "essonne",
    "hauts de seine",
    "seine saint denis",
    "val de marne",
    "val d oise",
    "ile de france",
}


def normalize(value: str) -> str:
    normalized = unicodedata.normalize(
        "NFKD",
        value,
    )
    without_accents = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )
    normalized_spaces = re.sub(
        r"\s+",
        " ",
        without_accents,
    )

    return normalized_spaces.strip().casefold()


def contains(text: str, keyword: str) -> bool:
    pattern = (
        rf"(?<![a-z0-9])"
        rf"{re.escape(keyword)}"
        rf"(?![a-z0-9])"
    )

    return re.search(pattern, text) is not None


def detected_skills(text: str) -> set[str]:
    normalized_text = normalize(text)

    return {
        canonical
        for canonical, aliases in SKILLS.items()
        if any(
            contains(
                normalized_text,
                normalize(alias),
            )
            for alias in aliases
        )
    }


def split_skill_segments(value: str) -> list[str]:
    return [
        segment.strip()
        for segment in re.split(
            r"[,;\n|]",
            value,
        )
        if segment.strip()
    ]


def segment_has_beginner_marker(segment: str) -> bool:
    normalized_segment = normalize(segment)

    return any(
        contains(
            normalized_segment,
            normalize(marker),
        )
        for marker in BEGINNER_MARKERS
    )


def detect_profile_skill_levels(
    profile: CandidateProfile,
) -> tuple[set[str], set[str]]:
    strong_skills: set[str] = set()
    beginner_skills: set[str] = set()

    for segment in split_skill_segments(profile.skills):
        segment_skills = detected_skills(segment)

        if segment_has_beginner_marker(segment):
            beginner_skills.update(segment_skills)
        else:
            strong_skills.update(segment_skills)

    role_skills = detected_skills(profile.target_roles)
    strong_skills.update(role_skills)

    beginner_skills -= strong_skills

    return strong_skills, beginner_skills


def calculate_skills_score(
    strong_skills: set[str],
    beginner_skills: set[str],
    offer_skills: set[str],
) -> tuple[int, list[str], list[str], list[str]]:
    if not offer_skills:
        return 0, [], [], []

    matched = sorted(
        offer_skills & strong_skills
    )
    skills_to_strengthen = sorted(
        offer_skills & beginner_skills
    )
    missing = sorted(
        offer_skills
        - strong_skills
        - beginner_skills
    )

    weighted_matches = (
        len(matched)
        + 0.5 * len(skills_to_strengthen)
    )

    score = round(
        35
        * weighted_matches
        / len(offer_skills)
    )

    return (
        score,
        matched,
        skills_to_strengthen,
        missing,
    )


def detect_role_domains(text: str) -> set[str]:
    normalized_text = normalize(text)
    domains: set[str] = set()

    role_aliases: dict[str, tuple[str, ...]] = {
        "cybersecurity": (
            "cybersecurite",
            "cyber security",
            "securite informatique",
            "analyste soc",
            "pentest",
        ),
        "cloud": (
            "cloud",
            "architecte cloud",
            "ingenieur cloud",
        ),
        "networking": (
            "reseau",
            "reseaux",
            "network",
            "administrateur systemes",
            "systemes et reseaux",
        ),
        "devsecops": (
            "devsecops",
            "devops",
        ),
        "artificial intelligence": (
            "intelligence artificielle",
            "artificial intelligence",
            "machine learning",
            "data science",
            "ingenieur ia",
            "ai engineer",
            "ml engineer",
        ),
    }

    for domain, aliases in role_aliases.items():
        if any(
            contains(
                normalized_text,
                normalize(alias),
            )
            for alias in aliases
        ):
            domains.add(domain)

    return domains


def calculate_role_match(
    profile: CandidateProfile,
    offer_text: str,
    profile_skills: set[str],
    offer_skills: set[str],
) -> bool:
    profile_domains = detect_role_domains(
        profile.target_roles
    )
    offer_domains = detect_role_domains(
        offer_text
    )

    if profile_domains & offer_domains:
        return True

    for domain, domain_skills in ROLE_DOMAINS.items():
        if (
            domain in profile_domains
            and domain_skills & offer_skills
        ):
            return True

    return bool(
        profile_skills
        & offer_skills
        & {
            "security",
            "networking",
            "cloud",
            "devsecops",
            "intelligence artificielle",
            "machine learning",
        }
    )


def calculate_contract_match(
    profile: CandidateProfile,
    offer: JobOffer,
) -> bool:
    del profile
    offer_text = normalize(
        f"{offer.title} {offer.contract_type} {offer.description}"
    )
    allowed_markers = (
        "alternance",
        "alternant",
        "apprentissage",
        "apprenti",
        "professionnalisation",
        "stage",
        "stagiaire",
        "internship",
        "intern ",
    )
    return any(marker in offer_text for marker in allowed_markers)


def calculate_experience_match(offer_text: str) -> bool:
    normalized_offer = normalize(offer_text)
    if any(
        marker in normalized_offer
        for marker in (
            "debutant accepte",
            "junior",
            "sans experience",
            "0 a 2 ans",
            "0-2 ans",
        )
    ):
        return True

    years = [
        int(value)
        for value in re.findall(
            r"(?<!\d)(\d{1,2})\s*(?:ans?|annees?|years?)(?!\w)",
            normalized_offer,
        )
    ]
    return not years or min(years) <= 2


PARTNER_SCHOOL_MARKERS = (
    "reserve aux etudiants de",
    "reservee aux etudiants de",
    "reserve aux etudiants inscrits",
    "en partenariat avec l ecole",
    "en partenariat avec notre ecole",
    "etudiants inscrits a l ecole",
    "dans le cadre d un partenariat avec l ecole",
    "uniquement pour les etudiants de l ecole",
    "ecole partenaire obligatoire",
    "cette offre est reservee aux eleves de",
)


def is_partner_school_offer(offer_text: str) -> bool:
    normalized_offer = normalize(offer_text).replace(
        "'", " "
    ).replace("’", " ")
    return any(
        marker in normalized_offer
        for marker in PARTNER_SCHOOL_MARKERS
    )


def calculate_freshness_score(offer: JobOffer) -> int:
    if offer.published_at is None:
        return 0
    published_at = offer.published_at
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    age_hours = max(
        0,
        (
            datetime.now(timezone.utc) - published_at
        ).total_seconds()
        / 3600,
    )
    if age_hours <= 24:
        return 5
    return 0


def extract_french_departments(
    location: str,
) -> set[str]:
    normalized_location = normalize(location)

    postal_codes = re.findall(
        r"(?<!\d)(\d{5})(?!\d)",
        normalized_location,
    )

    return {
        postal_code[:2]
        for postal_code in postal_codes
    }


def calculate_location_match(
    profile: CandidateProfile,
    offer: JobOffer,
) -> bool:
    profile_location = normalize(profile.location)
    offer_location = normalize(offer.location)
    offer_text = normalize(
        f"{offer.location} {offer.description}"
    )

    if any(
        marker in offer_text
        for marker in (
            "teletravail complet",
            "100% teletravail",
            "full remote",
            "remote france",
        )
    ):
        return True

    profile_targets_ile_de_france = any(
        name in profile_location
        for name in (
            "ile de france",
            "ile-de-france",
            "paris",
        )
    )

    offer_departments = extract_french_departments(
        offer.location
    )

    offer_is_in_ile_de_france = bool(
        offer_departments
        & ILE_DE_FRANCE_DEPARTMENTS
    ) or any(
        name in offer_location
        for name in ILE_DE_FRANCE_NAMES
    )

    if (
        profile_targets_ile_de_france
        and offer_is_in_ile_de_france
    ):
        return True

    profile_parts = [
        part.strip()
        for part in re.split(
            r"[,;]",
            profile_location,
        )
        if part.strip()
    ]

    return any(
        part in offer_location
        for part in profile_parts
    )


def calculate_education_match(
    profile: CandidateProfile,
    offer_text: str,
) -> bool:
    profile_education = normalize(
        f"{profile.education_level} {profile.program}"
    )
    normalized_offer = normalize(offer_text)

    profile_is_bac5 = any(
        value in profile_education
        for value in (
            "bac+5",
            "bac 5",
            "master",
            "niveau 7",
            "ingenieur",
        )
    )

    offer_requires_bac5 = any(
        value in normalized_offer
        for value in (
            "bac+5",
            "bac 5",
            "master",
            "niveau 7",
            "ecole d ingenieur",
            "cycle ingenieur",
        )
    )

    offer_has_explicit_lower_level = any(
        value in normalized_offer
        for value in (
            "bac+2",
            "bac 2",
            "niveau 5",
            "bts",
        )
    ) and not offer_requires_bac5

    if offer_requires_bac5:
        return profile_is_bac5

    if offer_has_explicit_lower_level:
        return False

    # Aucune exigence incompatible n’est indiquée.
    return True


def calculate_confidence(
    offer_skills: set[str],
    offer_domains: set[str],
) -> str:
    evidence_count = (
        len(offer_skills)
        + len(offer_domains)
    )

    if evidence_count >= 5:
        return "élevée"

    if evidence_count >= 3:
        return "moyenne"

    return "faible"


def format_skills(skills: list[str]) -> str:
    return ", ".join(skills)


def build_recommendations(
    *,
    score: int,
    matched_skills: list[str],
    skills_to_strengthen: list[str],
    missing_skills: list[str],
    role_match: bool,
    contract_match: bool,
    location_match: bool,
    education_match: bool,
    experience_match: bool,
    eligibility_reasons: list[str],
) -> tuple[str, str, list[str]]:
    if eligibility_reasons:
        decision = "rejected"
        application_priority = "blocked"
        actions = [
            "Offre écartée : " + "; ".join(eligibility_reasons) + "."
        ]
    elif score >= 60:
        decision = "documents_ready"
        application_priority = "high"
        actions = [
            (
                "Candidature recommandée : adapter le CV "
                "et préparer une candidature pour cette offre."
            )
        ]
    else:
        decision = "manual_review"
        application_priority = "medium"
        actions = [
            (
                "Offre admissible à examiner manuellement : "
                "le score est inférieur à 60/100."
            )
        ]

    if matched_skills:
        actions.append(
            (
                "Mettre en avant dans le CV : "
                f"{format_skills(matched_skills)}."
            )
        )

    if skills_to_strengthen:
        actions.append(
            (
                "Présenter comme notions et préparer un exemple "
                "concret pour : "
                f"{format_skills(skills_to_strengthen)}."
            )
        )

    if missing_skills:
        actions.append(
            (
                "Réviser avant un éventuel entretien : "
                f"{format_skills(missing_skills[:3])}."
            )
        )

    if not role_match:
        actions.append(
            (
                "Vérifier que les missions correspondent bien "
                "aux métiers recherchés."
            )
        )

    if not contract_match:
        actions.append(
            "Vérifier le type de contrat avant de postuler."
        )

    if not location_match:
        actions.append(
            (
                "Vérifier la localisation, le télétravail et "
                "les possibilités de déplacement."
            )
        )

    if not education_match:
        actions.append(
            (
                "Vérifier le niveau d’études demandé avant "
                "d’envoyer la candidature."
            )
        )

    if not experience_match:
        actions.append(
            "L’expérience demandée dépasse la cible de 0 à 2 ans."
        )

    return (
        decision,
        application_priority,
        actions,
    )


def calculate(
    profile: CandidateProfile,
    offer: JobOffer,
) -> dict[str, Any]:
    offer_text = (
        f"{offer.title} {offer.contract_type} "
        f"{offer.location} {offer.description}"
    )

    strong_skills, beginner_skills = (
        detect_profile_skill_levels(profile)
    )
    offer_skills = detected_skills(offer_text)
    technology_analysis = analyze_technologies(
        offer_text
    )

    (
        skills_score,
        matched_skills,
        skills_to_strengthen,
        missing_skills,
    ) = calculate_skills_score(
        strong_skills=strong_skills,
        beginner_skills=beginner_skills,
        offer_skills=offer_skills,
    )

    all_profile_skills = (
        strong_skills | beginner_skills
    )

    role_match = calculate_role_match(
        profile=profile,
        offer_text=offer_text,
        profile_skills=all_profile_skills,
        offer_skills=offer_skills,
    )
    role_score = 20 if role_match else 0

    contract_match = calculate_contract_match(
        profile,
        offer,
    )
    contract_score = 15 if contract_match else 0

    location_match = calculate_location_match(
        profile,
        offer,
    )
    location_score = 10 if location_match else 0

    education_match = calculate_education_match(
        profile,
        offer_text,
    )
    education_score = 5 if education_match else 0

    experience_match = calculate_experience_match(
        offer_text
    )
    experience_score = 10 if experience_match else 0
    freshness_score = calculate_freshness_score(offer)

    eligibility_reasons: list[str] = []
    priority_result = evaluate_priority_offer(offer)
    priority_reason_messages = {
        "offre_inactive": "offre déjà traitée ou archivée",
        "offre_plus_de_24_heures": "offre publiée depuis plus de 24 heures",
        "date_publication_future": "date de publication future",
        "offre_expiree": "offre expirée",
        "contrat_interdit": "contrat CDI, CDD ou autre contrat interdit",
        "contrat_non_reconnu": "contrat autre qu’alternance ou stage",
        "experience_superieure_a_2_ans": (
            "expérience demandée supérieure à 2 ans"
        ),
    }
    eligibility_reasons.extend(
        priority_reason_messages[reason]
        for reason in priority_result.reasons
        if reason in priority_reason_messages
    )
    if not contract_match:
        eligibility_reasons.append(
            "contrat autre qu’alternance ou stage"
        )
    if not location_match:
        eligibility_reasons.append(
            "localisation hors Île-de-France"
        )
    if not experience_match:
        eligibility_reasons.append(
            "expérience demandée supérieure à 2 ans"
        )
    if is_partner_school_offer(offer_text):
        eligibility_reasons.append(
            "offre réservée à une école partenaire spécifique"
        )
    if (
        not role_match
        and not matched_skills
        and not skills_to_strengthen
    ):
        eligibility_reasons.append(
            "aucun domaine ciblé ni technologie prouvée"
        )

    eligibility_reasons = list(
        dict.fromkeys(eligibility_reasons)
    )

    technology_count = (
        len(technology_analysis.known)
        + len(technology_analysis.unknown)
    )
    skills_score = (
        round(
            35
            * len(technology_analysis.known)
            / technology_count
        )
        if technology_count
        else 0
    )

    score = min(
        100,
        skills_score
        + role_score
        + contract_score
        + location_score
        + education_score
        + experience_score
        + freshness_score,
    )

    if score >= 85:
        recommendation = "Excellente compatibilité"
    elif score >= 70:
        recommendation = "Bonne compatibilité"
    elif score >= 50:
        recommendation = "Compatibilité moyenne"
    else:
        recommendation = "Compatibilité faible"

    confidence = calculate_confidence(
        offer_skills=offer_skills,
        offer_domains=detect_role_domains(
            offer_text
        ),
    )

    explanation = explain_score(
        total_score=score,
        known_skills=list(technology_analysis.known),
        unknown_skills=list(technology_analysis.unknown),
        blocking_reasons=eligibility_reasons,
    )

    (
        _legacy_decision,
        application_priority,
        actions,
    ) = build_recommendations(
        score=score,
        matched_skills=matched_skills,
        skills_to_strengthen=skills_to_strengthen,
        missing_skills=missing_skills,
        role_match=role_match,
        contract_match=contract_match,
        location_match=location_match,
        education_match=education_match,
        experience_match=experience_match,
        eligibility_reasons=eligibility_reasons,
    )

    result = {
        "score": score,
        "recommendation": recommendation,
        "confidence": confidence,
        "decision": explanation.decision,
        "application_priority": application_priority,
        "actions": actions,
        "matched_skills": matched_skills,
        "skills_to_strengthen": (
            skills_to_strengthen
        ),
        "missing_skills": missing_skills,
        "known_technologies": list(
            technology_analysis.known
        ),
        "unknown_technologies": list(
            technology_analysis.unknown
        ),
        "required_technologies": list(
            technology_analysis.required
        ),
        "preferred_technologies": list(
            technology_analysis.preferred
        ),
        "skills_score": skills_score,
        "role_score": role_score,
        "contract_score": contract_score,
        "location_score": location_score,
        "education_score": education_score,
        "experience_score": experience_score,
        "freshness_score": freshness_score,
        "role_match": role_match,
        "contract_match": contract_match,
        "location_match": location_match,
        "education_match": education_match,
        "experience_match": experience_match,
        "eligibility_reasons": eligibility_reasons,
    }
    log_event(
        logger,
        "offer_score_calculated",
        offer_id=offer.id,
        profile_id=profile.id,
        total_score=score,
        decision=explanation.decision,
        skills_score=skills_score,
        role_score=role_score,
        contract_score=contract_score,
        experience_score=experience_score,
        location_score=location_score,
        education_score=education_score,
        freshness_score=freshness_score,
        blocking_reasons=eligibility_reasons,
    )
    return result