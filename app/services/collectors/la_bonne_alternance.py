import os
import unicodedata
from collections.abc import Iterable
from datetime import datetime
from typing import Any

import httpx

from app.schemas import JobOfferCreate


LBA_SEARCH_URL = (
    "https://api.apprentissage.beta.gouv.fr"
    "/api/job/v1/search"
)

ILE_DE_FRANCE_DEPARTMENTS = [
    "75",
    "77",
    "78",
    "91",
    "92",
    "93",
    "94",
    "95",
]

TARGET_ROME_CODES = [
    "M1801",
    "M1802",
    "M1804",
    "M1805",
    "M1807",
]

TARGET_KEYWORDS = {
    "cybersecurite",
    "cyber security",
    "securite informatique",
    "securite des systemes",
    "soc",
    "siem",
    "cloud",
    "devsecops",
    "devops",
    "reseau",
    "network",
    "systeme",
    "administrateur systemes",
    "intelligence artificielle",
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "data scientist",
    "data science",
    "ingenieur ia",
    "ai engineer",
    "ml engineer",
}


class CollectorConfigurationError(RuntimeError):
    pass


class CollectorAPIError(RuntimeError):
    pass


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)

    without_accents = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )

    return " ".join(without_accents.casefold().split())


def is_relevant_offer(raw_offer: dict[str, Any]) -> bool:
    offer = raw_offer.get("offer") or {}

    searchable_text = normalize_text(
        " ".join(
            [
                str(offer.get("title") or ""),
                str(offer.get("description") or ""),
                " ".join(offer.get("desired_skills") or []),
                " ".join(
                    offer.get("to_be_acquired_skills") or []
                ),
            ]
        )
    )

    return any(
        keyword in searchable_text
        for keyword in TARGET_KEYWORDS
    )


def get_company_name(workplace: dict[str, Any]) -> str:
    for key in ("name", "brand", "legal_name"):
        value = workplace.get(key)

        if isinstance(value, str) and value.strip():
            return value.strip()

    return "Entreprise non renseignée"


def get_location(workplace: dict[str, Any]) -> str:
    location = workplace.get("location") or {}
    address = location.get("address")

    if isinstance(address, str) and address.strip():
        return address.strip()

    return "Île-de-France"


def get_contract_type(contract: dict[str, Any]) -> str:
    contract_types = contract.get("type") or []

    if isinstance(contract_types, list) and contract_types:
        return ", ".join(str(value) for value in contract_types)

    return "Alternance"


def get_source(raw_offer: dict[str, Any]) -> str:
    identifier = raw_offer.get("identifier") or {}
    partner_label = identifier.get("partner_label")

    if isinstance(partner_label, str) and partner_label.strip():
        return f"La Bonne Alternance - {partner_label.strip()}"

    return "La Bonne Alternance"


def get_source_url(raw_offer: dict[str, Any]) -> str | None:
    apply_data = raw_offer.get("apply") or {}
    url = apply_data.get("url")

    if isinstance(url, str) and url.strip():
        return url.strip()

    return None


def get_published_at(
    raw_offer: dict[str, Any],
) -> datetime | None:
    offer = raw_offer.get("offer") or {}
    publication = offer.get("publication") or {}
    creation = publication.get("creation")

    from app.services.priority_filter import (
        parse_platform_datetime,
    )

    return parse_platform_datetime(creation)


def transform_offer(
    raw_offer: dict[str, Any],
) -> JobOfferCreate:
    offer = raw_offer.get("offer") or {}
    workplace = raw_offer.get("workplace") or {}
    contract = raw_offer.get("contract") or {}

    return JobOfferCreate(
        title=str(
            offer.get("title") or "Offre sans titre"
        ).strip(),
        company=get_company_name(workplace),
        location=get_location(workplace),
        contract_type=get_contract_type(contract),
        description=str(
            offer.get("description")
            or "Description indisponible pour cette offre."
        ).strip(),
        source=get_source(raw_offer),
        source_url=get_source_url(raw_offer),
        published_at=get_published_at(raw_offer),
    )


class LaBonneAlternanceCollector:
    def __init__(
        self,
        api_key: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("LBA_API_KEY")

        if not self.api_key:
            raise CollectorConfigurationError(
                "LBA_API_KEY is not configured"
            )

        self.client = client or httpx.Client(
            timeout=30.0,
        )
        self._owns_client = client is None

    def _build_params(
        self,
    ) -> list[tuple[str, str]]:
        params = [
            (
                "romes",
                ",".join(TARGET_ROME_CODES),
            ),
            ("target_diploma_level", "7"),
        ]

        params.extend(
            ("departements", department)
            for department in ILE_DE_FRANCE_DEPARTMENTS
        )

        return params

    def fetch_raw_offers(
        self,
    ) -> list[dict[str, Any]]:
        try:
            response = self.client.get(
                LBA_SEARCH_URL,
                headers={
                    "Authorization": (
                        f"Bearer {self.api_key}"
                    ),
                    "Accept": "application/json",
                },
                params=self._build_params(),
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise CollectorAPIError(
                "La Bonne Alternance API request failed"
            ) from error

        payload = response.json()
        jobs = payload.get("jobs")

        if not isinstance(jobs, list):
            raise CollectorAPIError(
                "Invalid La Bonne Alternance response"
            )

        return [
            job
            for job in jobs
            if isinstance(job, dict)
        ]

    def collect(self) -> list[JobOfferCreate]:
        raw_offers = self.fetch_raw_offers()

        return [
            transform_offer(raw_offer)
            for raw_offer in raw_offers
            if is_relevant_offer(raw_offer)
        ]

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def __enter__(
        self,
    ) -> "LaBonneAlternanceCollector":
        return self

    def __exit__(
        self,
        *_: object,
    ) -> None:
        self.close()


def collect_lba_offers(
    api_key: str | None = None,
) -> Iterable[JobOfferCreate]:
    with LaBonneAlternanceCollector(
        api_key=api_key,
    ) as collector:
        return collector.collect()
