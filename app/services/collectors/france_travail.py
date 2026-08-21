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
    extract_experience_range,
    parse_platform_datetime,
)


TOKEN_URL = (
    "https://entreprise.francetravail.fr/connexion/"
    "oauth2/access_token"
)
SEARCH_URL = (
    "https://api.francetravail.io/partenaire/"
    "offresdemploi/v2/offres/search"
)
SEARCH_QUERIES = (
    "alternance cybersécurité cloud",
    "alternance réseau devsecops",
    "alternance intelligence artificielle stage informatique",
)
ILE_DE_FRANCE_DEPARTMENTS = (
    "75",
    "77",
    "78",
    "91",
    "92",
    "93",
    "94",
    "95",
)


def parse_datetime(value: object) -> datetime | None:
    return parse_platform_datetime(value)


def is_relevant_offer(raw_offer: dict[str, Any]) -> bool:
    text = normalize_text(
        " ".join(
            [
                str(raw_offer.get("intitule") or ""),
                str(raw_offer.get("description") or ""),
                str(
                    raw_offer.get("typeContratLibelle")
                    or ""
                ),
            ]
        )
    )

    is_alternance = any(
        word in text
        for word in (
            "alternance",
            "apprentissage",
            "professionnalisation",
            "stage",
            "stagiaire",
            "internship",
        )
    )
    is_targeted = any(
        keyword in text
        for keyword in TARGET_KEYWORDS
    )

    return is_alternance and is_targeted


def transform_offer(
    raw_offer: dict[str, Any],
) -> JobOfferCreate:
    company = raw_offer.get("entreprise") or {}
    workplace = raw_offer.get("lieuTravail") or {}
    origin = raw_offer.get("origineOffre") or {}
    description = str(
        raw_offer.get("description")
        or "Description indisponible pour cette offre."
    ).strip()
    experience_min, experience_max = extract_experience_range(
        description
    )
    raw_contract = str(
        raw_offer.get("typeContratLibelle") or ""
    ).strip()
    normalized_contract_text = normalize_text(
        f"{raw_contract} {description}"
    )
    contract_type = raw_contract or "Alternance"
    if any(
        marker in normalized_contract_text
        for marker in ("stage", "stagiaire", "internship")
    ):
        contract_type = "Stage"
    elif any(
        marker in normalized_contract_text
        for marker in (
            "alternance",
            "apprentissage",
            "professionnalisation",
        )
    ):
        contract_type = "Alternance"
    external_id = str(raw_offer.get("id") or "").strip() or None
    source_url = (
        origin.get("urlOrigine")
        or raw_offer.get("urlPostulation")
        or (
            "https://candidat.francetravail.fr/offres/"
            f"recherche/detail/{external_id}"
            if external_id
            else None
        )
    )

    return JobOfferCreate(
        title=str(
            raw_offer.get("intitule")
            or "Offre sans titre"
        ).strip(),
        company=str(
            company.get("nom")
            or "Entreprise non renseignée"
        ).strip(),
        location=str(
            workplace.get("libelle")
            or "Île-de-France"
        ).strip(),
        contract_type=contract_type,
        description=description,
        source="France Travail",
        external_id=external_id,
        source_url=source_url,
        published_at=parse_datetime(
            raw_offer.get("dateCreation"),
        ),
        experience_min=experience_min,
        experience_max=experience_max,
        application_channel="official_api",
    )


class FranceTravailCollector:
    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.client_id = client_id or os.getenv(
            "FRANCE_TRAVAIL_CLIENT_ID",
        )
        self.client_secret = client_secret or os.getenv(
            "FRANCE_TRAVAIL_CLIENT_SECRET",
        )

        if not self.client_id or not self.client_secret:
            raise CollectorConfigurationError(
                "France Travail credentials are not configured"
            )

        self.client = client or httpx.Client(timeout=30.0)
        self._owns_client = client is None

    def get_access_token(self) -> str:
        try:
            response = self.client.post(
                TOKEN_URL,
                params={"realm": "/partenaire"},
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": (
                        "api_offresdemploiv2 o2dsoffre"
                    ),
                },
                headers={
                    "Content-Type": (
                        "application/x-www-form-urlencoded"
                    ),
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise CollectorAPIError(
                "France Travail authentication failed"
            ) from error

        token = response.json().get("access_token")

        if not isinstance(token, str) or not token:
            raise CollectorAPIError(
                "Invalid France Travail token response"
            )

        return token

    def collect(self) -> list[JobOfferCreate]:
        token = self.get_access_token()
        collected: dict[str, dict[str, Any]] = {}

        for department in ILE_DE_FRANCE_DEPARTMENTS:
            for query in SEARCH_QUERIES:
                try:
                    response = self.client.get(
                        SEARCH_URL,
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Accept": "application/json",
                        },
                        params={
                            "motsCles": query,
                            "departement": department,
                            "range": "0-49",
                        },
                    )
                    response.raise_for_status()
                except httpx.HTTPError as error:
                    raise CollectorAPIError(
                        "France Travail API request failed"
                    ) from error

                results = response.json().get("resultats")

                if not isinstance(results, list):
                    raise CollectorAPIError(
                        "Invalid France Travail response"
                    )

                for item in results:
                    if not isinstance(item, dict):
                        continue
                    identifier = str(
                        item.get("id")
                        or item.get("urlPostulation")
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

    def __enter__(self) -> "FranceTravailCollector":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def collect_france_travail_offers() -> list[JobOfferCreate]:
    with FranceTravailCollector() as collector:
        return collector.collect()
