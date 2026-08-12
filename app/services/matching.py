import re
import unicodedata
from typing import Any

from app.models import CandidateProfile, JobOffer


SKILLS: dict[str, tuple[str, ...]] = {
    "python": ("python",),
    "fastapi": ("fastapi",),
    "react": ("react",),
    "typescript": ("typescript",),
    "docker": ("docker",),
    "linux": ("linux",),
    "kubernetes": ("kubernetes", "k8s"),
    "terraform": ("terraform",),
    "azure": ("azure",),
    "aws": ("aws", "amazon web services"),
    "networking": ("networking", "reseau", "reseaux", "network"),
    "security": ("security", "securite", "cybersecurite", "securisation"),
    "cloud": ("cloud",),
    "devsecops": ("devsecops",),
    "ci/cd": ("ci/cd", "cicd", "github actions"),
    "postgresql": ("postgresql", "postgres"),
    "sql": ("sql",),
    "rbac": ("rbac",),
    "jwt": ("jwt",),
    "prometheus": ("prometheus",),
    "grafana": ("grafana",),
}


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return value.casefold()


def contains(text: str, keyword: str) -> bool:
    pattern = rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])"
    return re.search(pattern, text) is not None


def detected_skills(text: str) -> set[str]:
    normalized = normalize(text)
    return {
        canonical
        for canonical, aliases in SKILLS.items()
        if any(contains(normalized, normalize(alias)) for alias in aliases)
    }


def calculate(profile: CandidateProfile, offer: JobOffer) -> dict[str, Any]:
    profile_text = f"{profile.skills} {profile.target_roles}"
    offer_text = f"{offer.title} {offer.description}"
    profile_skills = detected_skills(profile_text)
    offer_skills = detected_skills(offer_text)
    matched = sorted(profile_skills & offer_skills)
    missing = sorted(offer_skills - profile_skills)

    skills_score = round(60 * len(matched) / max(len(offer_skills), 1))
    roles = [part.strip() for part in re.split(r"[,;]", normalize(profile.target_roles))]
    role_match = any(role and role in normalize(offer_text) for role in roles)
    if not role_match:
        role_match = bool(
            {"security", "networking", "cloud", "devsecops"}
            & profile_skills
            & offer_skills
        )
    role_score = 20 if role_match else 0

    contract_match = normalize(profile.target_contract) in normalize(offer.contract_type)
    contract_score = 10 if contract_match else 0

    profile_location = normalize(profile.location)
    offer_location = normalize(offer.location)
    location_match = any(
        token.strip() and token.strip() in offer_location
        for token in re.split(r"[,;]", profile_location)
    ) or "ile-de-france" in profile_location and "paris" in offer_location
    location_score = 10 if location_match else 0

    score = min(100, skills_score + role_score + contract_score + location_score)
    if score >= 85:
        recommendation = "Excellente compatibilité"
    elif score >= 70:
        recommendation = "Bonne compatibilité"
    elif score >= 50:
        recommendation = "Compatibilité moyenne"
    else:
        recommendation = "Compatibilité faible"

    return {
        "score": score,
        "recommendation": recommendation,
        "matched_skills": matched,
        "missing_skills": missing,
        "skills_score": skills_score,
        "role_score": role_score,
        "contract_score": contract_score,
        "location_score": location_score,
        "role_match": role_match,
        "contract_match": contract_match,
        "location_match": location_match,
    }
