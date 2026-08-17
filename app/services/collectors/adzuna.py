import os
from datetime import datetime
from typing import Any

import httpx

from app.schemas import JobOfferCreate
from app.services.collectors.la_bonne_alternance import (
    CollectorAPIError,
    CollectorConfigurationError,
    TARGET_KEYWORDS,
    normalize_text,
)


SEARCH_URL = (
    "https://api.adzuna.com/v1/api/jobs/fr/search/1"
)
SEARCH_QUERIES = (
    "alternance cybersécurité",
    "alternance cloud devops réseau",
    "alternance intelligence artificielle",
)


def parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00"),
        )
    except ValueError:
        return None


def is_relevant_offer(raw_offer: dict[str, Any]) -> bool:
    text = normalize_text(
        " ".join(
            [
                str(raw_offer.get("title") or ""),
                str(raw_offer.get("description") or ""),
                str(raw_offer.get("contract_type") or ""),
            ]
        )
    )

    return (
        any(
            word in text
            for word in (
                "alternance",
                "apprentissage",
                "professionnalisation",
            )
        )
        and any(
            keyword in text
            for keyword in TARGET_KEYWORDS
        )
    )


def transform_offer(
    raw_offer: dict[str, Any],
) -> JobOfferCreate:
    company = raw_offer.get("company") or {}
    location = raw_offer.get("location") or {}

    return JobOfferCreate(
        title=str(
            raw_offer.get("title")
            or "Offre sans titre"
        ).strip(),
        company=str(
            company.get("display_name")
            or "Entreprise non renseignée"
        ).strip(),
        location=str(
            location.get("display_name")
            or "Île-de-France"
        ).strip(),
        contract_type=str(
            raw_offer.get("contract_type")
            or "Alternance"
        ).strip(),
        description=str(
            raw_offer.get("description")
            or "Description indisponible pour cette offre."
        ).strip(),
        source="Adzuna",
        source_url=raw_offer.get("redirect_url"),
        published_at=parse_datetime(
            raw_offer.get("created"),
        ),
    )


class AdzunaCollector:
    def __init__(
        self,
        app_id: str | None = None,
        app_key: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.app_id = app_id or os.getenv("ADZUNA_APP_ID")
        self.app_key = app_key or os.getenv("ADZUNA_APP_KEY")

        if not self.app_id or not self.app_key:
            raise CollectorConfigurationError(
                "Adzuna credentials are not configured"
            )

        self.client = client or httpx.Client(timeout=30.0)
        self._owns_client = client is None

    def collect(self) -> list[JobOfferCreate]:
        collected: dict[str, dict[str, Any]] = {}

        for query in SEARCH_QUERIES:
            try:
                response = self.client.get(
                    SEARCH_URL,
                    params={
                        "app_id": self.app_id,
                        "app_key": self.app_key,
                        "results_per_page": 50,
                        "what": query,
                        "where": "Île-de-France",
                        "content-type": "application/json",
                    },
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
            except httpx.HTTPError as error:
                raise CollectorAPIError(
                    "Adzuna API request failed"
                ) from error

            results = response.json().get("results")

            if not isinstance(results, list):
                raise CollectorAPIError(
                    "Invalid Adzuna response"
                )

            for item in results:
                if isinstance(item, dict):
                    identifier = str(
                        item.get("id")
                        or item.get("redirect_url")
                        or len(collected)
                    )
                    collected[identifier] = item

        return [
            transform_offer(item)
            for item in collected.values()
            if is_relevant_offer(item)
        ]

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def __enter__(self) -> "AdzunaCollector":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def collect_adzuna_offers() -> list[JobOfferCreate]:
    with AdzunaCollector() as collector:
        return collector.collect()
