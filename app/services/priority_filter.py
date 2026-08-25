import re
import logging
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from dateutil import parser as date_parser

from app.models import JobOffer
from app.observability import log_event


logger = logging.getLogger(__name__)


PARIS_TIMEZONE = ZoneInfo("Europe/Paris")
MAXIMUM_OFFER_AGE = timedelta(hours=24)
MAXIMUM_EXPERIENCE_YEARS = 2

ALLOWED_CONTRACT_PATTERN = re.compile(
    r"\b(?:alternance|alternant(?:e)?|apprenti(?:e)?|apprentissage|"
    r"professionnalisation|stage|stagiaire|internship|trainee)\b",
    re.IGNORECASE,
)
REJECTED_CONTRACT_PATTERN = re.compile(
    r"\b(?:cdi|cdd|interim|freelance|independant|permanent|"
    r"fixed[ -]?term)\b",
    re.IGNORECASE,
)
EXPERIENCE_RANGE_PATTERN = re.compile(
    r"\b(\d{1,2})\s*(?:a|à|au|-|–|—)\s*(\d{1,2})\s*ans?\b",
    re.IGNORECASE,
)
EXPERIENCE_SINGLE_PATTERNS = (
    re.compile(
        r"\b(\d{1,2})\s*ans?\s+(?:d['’ ]?)?experience\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bexperience\s+(?:de\s+|minimum\s+|requise\s*:?[ ]*)?"
        r"(\d{1,2})\s*ans?\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:minimum|min\.?|au moins)\s+(\d{1,2})\s*ans?\b",
        re.IGNORECASE,
    ),
)
BEGINNER_PATTERN = re.compile(
    r"\b(?:debutant(?:e)?|junior|sans experience|premiere experience|"
    r"0\s*(?:a|à|-|–)\s*2\s*ans?)\b",
    re.IGNORECASE,
)

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
    normalized_offer = normalize_text(offer_text).replace(
        "'", " "
    ).replace("’", " ")
    return any(
        marker in normalized_offer
        for marker in PARTNER_SCHOOL_MARKERS
    )


@dataclass(frozen=True)
class PriorityFilterResult:
    eligible: bool
    reasons: tuple[str, ...]
    age_hours: float | None
    experience_min: int | None
    experience_max: int | None


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )

    return " ".join(without_accents.casefold().split())


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=PARIS_TIMEZONE)

    return value.astimezone(timezone.utc)


def parse_platform_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return ensure_utc(value)

    if not isinstance(value, str) or not value.strip():
        return None

    try:
        parsed = date_parser.parse(
            value.strip(),
            dayfirst=True,
        )
    except (OverflowError, TypeError, ValueError):
        return None

    return ensure_utc(parsed)


def extract_experience_range(
    text: str,
) -> tuple[int | None, int | None]:
    normalized = normalize_text(text)
    range_match = EXPERIENCE_RANGE_PATTERN.search(normalized)

    if range_match:
        minimum = int(range_match.group(1))
        maximum = int(range_match.group(2))
        return min(minimum, maximum), max(minimum, maximum)

    for pattern in EXPERIENCE_SINGLE_PATTERNS:
        match = pattern.search(normalized)
        if match:
            years = int(match.group(1))
            return years, years

    if BEGINNER_PATTERN.search(normalized):
        return 0, 2

    return None, None


def evaluate_priority_offer(
    offer: JobOffer,
    *,
    now: datetime | None = None,
) -> PriorityFilterResult:
    reasons: list[str] = []
    current_time = ensure_utc(now or datetime.now(timezone.utc))

    if offer.status in {"applied", "rejected", "archived"}:
        reasons.append("offre_inactive")

    published_at = (
        ensure_utc(offer.published_at)
        if offer.published_at is not None
        else None
    )
    age_hours: float | None = None

    if published_at is None:
        reasons.append("date_publication_inconnue")
    else:
        age = current_time - published_at
        age_hours = age.total_seconds() / 3600

        if age < timedelta(minutes=-5):
            reasons.append("date_publication_future")
        elif age > MAXIMUM_OFFER_AGE:
            reasons.append("offre_plus_de_24_heures")

    if (
        offer.expires_at is not None
        and ensure_utc(offer.expires_at) <= current_time
    ):
        reasons.append("offre_expiree")

    # Les collecteurs (Choisir le Service Public notamment) valident le
    # mot "alternance"/"apprentissage" sur l'ensemble titre + métier +
    # spécialisation + compétences + contrat lors de la collecte - ces
    # champs (hors titre) sont regroupés dans la description de l'offre.
    # Ne vérifier que titre + type de contrat ici rejetait donc à tort
    # des offres pourtant bien alternance/stage.
    contract_text = normalize_text(
        f"{offer.title} {offer.contract_type} {offer.description}"
    )

    if REJECTED_CONTRACT_PATTERN.search(contract_text):
        reasons.append("contrat_interdit")
    elif not ALLOWED_CONTRACT_PATTERN.search(contract_text):
        reasons.append("contrat_non_reconnu")

    if is_partner_school_offer(
        f"{offer.title} {offer.description}"
    ):
        reasons.append("offre_reservee_ecole_partenaire")

    experience_min = offer.experience_min
    experience_max = offer.experience_max

    if experience_min is None and experience_max is None:
        experience_min, experience_max = extract_experience_range(
            f"{offer.title} {offer.description}"
        )

    # Expérience non précisée dans l'offre : on ne rejette plus dans ce
    # cas. Le contrat est déjà vérifié juste au-dessus (alternance/stage
    # uniquement), ce qui implique par nature un profil débutant - c'est
    # d'ailleurs déjà comme ça que calculate_experience_match() dans
    # matching.py traite ce cas (permissif quand l'info est absente).
    if experience_min is None and experience_max is None:
        pass
    elif (
        (experience_min is not None and experience_min > MAXIMUM_EXPERIENCE_YEARS)
        or (experience_max is not None and experience_max > MAXIMUM_EXPERIENCE_YEARS)
    ):
        reasons.append("experience_superieure_a_2_ans")

    result = PriorityFilterResult(
        eligible=not reasons,
        reasons=tuple(reasons),
        age_hours=age_hours,
        experience_min=experience_min,
        experience_max=experience_max,
    )
    log_event(
        logger,
        "offer_filter_evaluated",
        offer_id=offer.id,
        source=offer.source,
        eligible=result.eligible,
        reasons=list(result.reasons),
        age_hours=result.age_hours,
        experience_min=result.experience_min,
        experience_max=result.experience_max,
    )
    return result
