import html
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


def is_target_offer(*values: Any) -> bool:
    searchable = normalize_text(
        " ".join(clean_html(value) for value in values)
    )
    return (
        any(word in searchable for word in TARGET_KEYWORDS)
        and any(word in searchable for word in ALTERNANCE_KEYWORDS)
    )


def parse_datetime(value: Any) -> datetime | None:
    return parse_platform_datetime(value)


def comma_separated_environment(value: str | None) -> list[str]:
    return [
        item.strip()
        for item in (value or "").split(",")
        if item.strip()
    ]
