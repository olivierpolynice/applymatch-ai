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
from app.services.priority_filter import (
    parse_platform_datetime,
)


SEARCH_URL = "https://jooble.org/api/{api_key}"
SEARCH_QUERIES = (
    "alternance cybersécurité",
    "alternance cloud devops réseau",
    "alternance intelligence artificielle",
)


def parse_datetime(value: object) -> datetime | None:
    return parse_platform_datetime(value)


def is_relevant_offer(raw_offer: dict[str, Any]) -> bool:
    text = normalize_text(
        " ".join(
            [
                str(raw_offer.get("title") or ""),
                str(raw_offer.get("snippet") or ""),
                str(raw_offer.get("type") or ""),
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
    return JobOfferCreate(
        title=str(
            raw_offer.get("title")
            or "Offre sans titre"
        ).strip(),
        company=str(
            raw_offer.get("company")
            or "Entreprise non renseignée"
        ).strip(),
        location=str(
            raw_offer.get("location")
            or "Île-de-France"
        ).strip(),
        contract_type=str(
            raw_offer.get("type")
            or "Alternance"
        ).strip(),
        description=str(
            raw_offer.get("snippet")
            or "Description indisponible pour cette offre."
        ).strip(),
        source="Jooble",
        source_url=raw_offer.get("link"),
        published_at=parse_datetime(
            raw_offer.get("updated"),
        ),
    )


class JoobleCollector:
    def __init__(
        self,
        api_key: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("JOOBLE_API_KEY")

        if not self.api_key:
            raise CollectorConfigurationError(
                "JOOBLE_API_KEY is not configured"
            )

        self.client = client or httpx.Client(timeout=30.0)
        self._owns_client = client is None

    def collect(self) -> list[JobOfferCreate]:
        collected: dict[str, dict[str, Any]] = {}

        for query in SEARCH_QUERIES:
            try:
                response = self.client.post(
                    SEARCH_URL.format(api_key=self.api_key),
                    json={
                        "keywords": query,
                        "location": "Île-de-France",
                        "page": 1,
                    },
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
            except httpx.HTTPError as error:
                raise CollectorAPIError(
                    "Jooble API request failed"
                ) from error

            jobs = response.json().get("jobs")

            if not isinstance(jobs, list):
                raise CollectorAPIError(
                    "Invalid Jooble response"
                )

            for item in jobs:
                if isinstance(item, dict):
                    identifier = str(
                        item.get("id")
                        or item.get("link")
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

    def __enter__(self) -> "JoobleCollector":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def collect_jooble_offers() -> list[JobOfferCreate]:
    with JoobleCollector() as collector:
        return collector.collect()
