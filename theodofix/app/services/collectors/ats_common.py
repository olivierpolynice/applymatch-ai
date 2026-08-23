import html
import os
import re
from datetime import datetime
from typing import Any

from app.services.collectors.la_bonne_alternance import (
    TARGET_KEYWORDS,
    normalize_text,
)
from app.services.priority_filter import (
    parse_platform_datetime,
)


ALTERNANCE_KEYWORDS = {
    "alternance",
    "alternant",
    "apprenti",
    "apprentissage",
    "contrat de professionnalisation",
}

# Un titre qui affiche explicitement un de ces mots est un poste classique
# (CDI/CDD), pas une alternance — même si le mot "alternance" traîne
# ailleurs dans la description (ex: mention générique de l'entreprise).
EXCLUDED_TITLE_CONTRACT_KEYWORDS = {
    "cdi",
    "cdd",
}


def clean_html(value: Any) -> str:
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    return " ".join(html.unescape(text).split())


def normalize_description(value: Any) -> str:
    description = clean_html(value)
    if len(description) >= 20:
        return description
    if description:
        return (
            f"{description}. Informations complémentaires "
            "indisponibles pour cette offre."
        )
    return "Description détaillée indisponible pour cette offre."


def title_has_excluded_contract_keyword(title: Any) -> bool:
    """True si le titre annonce explicitement un CDI/CDD.

    Les collecteurs appellent tous is_target_offer(title, ...) avec le
    titre en premier argument : c'est le signal le plus fiable, car un
    intitulé de poste indique son type de contrat directement quand ce
    n'est pas une alternance ("... CDI Paris ..."), contrairement à la
    description qui peut mentionner "alternance" sans rapport avec le
    poste (mention générique de l'entreprise, autres offres, etc.).
    """
    words = set(
        normalize_text(clean_html(title)).split()
    )
    return any(
        word in words
        for word in EXCLUDED_TITLE_CONTRACT_KEYWORDS
    )


def is_target_offer(*values: Any) -> bool:
    if values and title_has_excluded_contract_keyword(values[0]):
        return False

    searchable = normalize_text(
        " ".join(clean_html(value) for value in values)
    )
    return (
        any(word in searchable for word in TARGET_KEYWORDS)
        and any(word in searchable for word in ALTERNANCE_KEYWORDS)
    )


def get_blocked_companies() -> set[str]:
    """Entreprises à exclure entièrement de la collecte (ATS par entreprise).

    Configurée via la variable d'environnement COLLECTOR_COMPANY_BLOCKLIST,
    une liste séparée par des virgules (ex: "theodo,autre-entreprise").
    Comparaison insensible à la casse et aux accents.
    """
    return {
        normalize_text(item)
        for item in comma_separated_environment(
            os.getenv("COLLECTOR_COMPANY_BLOCKLIST")
        )
    }


def is_blocked_company(
    company: Any,
    blocked_companies: set[str] | None = None,
) -> bool:
    blocked = (
        blocked_companies
        if blocked_companies is not None
        else get_blocked_companies()
    )
    return normalize_text(str(company or "")) in blocked


def parse_datetime(value: Any) -> datetime | None:
    return parse_platform_datetime(value)


def comma_separated_environment(value: str | None) -> list[str]:
    return [
        item.strip()
        for item in (value or "").split(",")
        if item.strip()
    ]
