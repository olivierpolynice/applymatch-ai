import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

from rapidfuzz import fuzz, process

from app.services.profile_loader import (
    TechnologyDefinition,
    load_profile,
)


FUZZY_THRESHOLD = 92
REQUIRED_MARKERS = (
    "obligatoire",
    "obligatoires",
    "requis",
    "requise",
    "required",
    "indispensable",
    "exige",
    "exigee",
    "maitrise de",
    "maitriser",
    "must have",
)
PREFERRED_MARKERS = (
    "souhaite",
    "souhaitee",
    "apprecie",
    "appreciee",
    "serait un plus",
    "nice to have",
    "idealement",
)

# Technologies recherchées dans les annonces même lorsqu'elles ne sont pas
# présentes dans le profil. Elles seront alors classées comme inconnues.
DISCOVERY_ALIASES: dict[str, tuple[str, ...]] = {
    "Active Directory": ("active directory", "azure ad", "entra id"),
    "Ansible": ("ansible",),
    "AWS": ("aws", "amazon web services"),
    "Azure": ("azure", "microsoft azure"),
    "Celery": ("celery",),
    "GCP": ("gcp", "google cloud platform", "google cloud"),
    "GitLab CI": ("gitlab ci", "gitlab-ci"),
    "Jenkins": ("jenkins",),
    "Kubernetes": ("kubernetes", "k8s"),
    "LangChain": ("langchain",),
    "OpenAI API": ("openai api", "api openai"),
    "QRadar": ("qradar",),
    "RAG": ("rag", "retrieval augmented generation"),
    "Redis": ("redis",),
    "SIEM": ("siem",),
    "Splunk": ("splunk",),
    "Microsoft Sentinel": ("microsoft sentinel", "azure sentinel"),
    "Terraform": ("terraform",),
}


@dataclass(frozen=True)
class TechnologyAnalysis:
    known: tuple[str, ...]
    unknown: tuple[str, ...]
    required: tuple[str, ...]
    preferred: tuple[str, ...]
    evidence: dict[str, tuple[str, ...]]


def normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )
    cleaned = re.sub(r"\s+", " ", without_accents)

    return cleaned.strip().casefold()


def contains_alias(text: str, alias: str) -> bool:
    normalized_alias = normalize(alias)
    pattern = (
        rf"(?<![a-z0-9]){re.escape(normalized_alias)}(?![a-z0-9])"
    )
    return re.search(pattern, text) is not None


def candidate_phrases(text: str, maximum_words: int = 4) -> list[str]:
    words = re.findall(r"[a-z0-9+#./-]+", text)
    phrases: list[str] = []

    for size in range(1, maximum_words + 1):
        phrases.extend(
            " ".join(words[index : index + size])
            for index in range(0, len(words) - size + 1)
        )

    return phrases


def alias_is_detected(
    normalized_text: str,
    phrases: list[str],
    alias: str,
) -> bool:
    normalized_alias = normalize(alias)

    if contains_alias(normalized_text, normalized_alias):
        return True

    # Les alias très courts (IA, AI, JS, TS...) ne sont jamais comparés de
    # manière floue afin d'éviter les faux positifs.
    compact_alias = re.sub(r"[^a-z0-9]", "", normalized_alias)
    if len(compact_alias) < 4:
        return False

    best_match = process.extractOne(
        normalized_alias,
        phrases,
        scorer=fuzz.WRatio,
        score_cutoff=FUZZY_THRESHOLD,
    )

    return best_match is not None


def requirement_for_aliases(
    normalized_text: str,
    aliases: tuple[str, ...],
) -> str:
    clauses = re.split(r"[.;\n]", normalized_text)

    for clause in clauses:
        if not any(contains_alias(clause, alias) for alias in aliases):
            continue

        if any(marker in clause for marker in REQUIRED_MARKERS):
            return "required"

        if any(marker in clause for marker in PREFERRED_MARKERS):
            return "preferred"

    return "mentioned"


@lru_cache(maxsize=1)
def verified_catalog() -> tuple[TechnologyDefinition, ...]:
    document = load_profile()
    return tuple(
        technology
        for technology in document.technologies
        if technology.evidence
    )


def clear_catalog_cache() -> None:
    verified_catalog.cache_clear()


def analyze_technologies(
    text: str,
    *,
    catalog: tuple[TechnologyDefinition, ...] | None = None,
) -> TechnologyAnalysis:
    normalized_text = normalize(text)
    phrases = candidate_phrases(normalized_text)
    verified = catalog if catalog is not None else verified_catalog()

    definitions: dict[str, tuple[str, ...]] = {
        technology.name: tuple(
            dict.fromkeys([technology.name, *technology.aliases])
        )
        for technology in verified
    }

    for name, aliases in DISCOVERY_ALIASES.items():
        definitions.setdefault(name, aliases)

    verified_by_normalized_name = {
        normalize(technology.name): technology
        for technology in verified
    }
    known: set[str] = set()
    unknown: set[str] = set()
    required: set[str] = set()
    preferred: set[str] = set()
    evidence: dict[str, tuple[str, ...]] = {}

    for name, aliases in definitions.items():
        if not any(
            alias_is_detected(normalized_text, phrases, alias)
            for alias in aliases
        ):
            continue

        verified_technology = verified_by_normalized_name.get(
            normalize(name)
        )

        if verified_technology is not None:
            known.add(verified_technology.name)
            evidence[verified_technology.name] = tuple(
                verified_technology.evidence
            )
            display_name = verified_technology.name
        else:
            unknown.add(name)
            display_name = name

        requirement = requirement_for_aliases(
            normalized_text,
            aliases,
        )

        if requirement == "required":
            required.add(display_name)
        elif requirement == "preferred":
            preferred.add(display_name)

    return TechnologyAnalysis(
        known=tuple(sorted(known)),
        unknown=tuple(sorted(unknown)),
        required=tuple(sorted(required)),
        preferred=tuple(sorted(preferred)),
        evidence=evidence,
    )
