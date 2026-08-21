import csv
from datetime import date, datetime
from zoneinfo import ZoneInfo

import httpx

from app.schemas import JobOfferCreate
from app.services.collectors.ats_common import (
    is_target_offer,
    normalize_description,
)
from app.services.collectors.la_bonne_alternance import (
    CollectorAPIError,
)


CSP_RESOURCE_URL = (
    "https://www.data.gouv.fr/api/1/datasets/r/"
    "867034a2-2fa1-41b4-bd39-c84691ea618f"
)
MAX_RESULTS = 200
PARIS_TIMEZONE = ZoneInfo("Europe/Paris")


def _parse_date(value: str) -> datetime | None:
    try:
        parsed_date = datetime.strptime(
            value.strip(),
            "%d/%m/%Y",
        )

        return parsed_date.replace(
            tzinfo=PARIS_TIMEZONE,
        )
    except (TypeError, ValueError):
        return None


def _is_active(row: dict[str, str]) -> bool:
    end_date = _parse_date(
        row.get("Date de fin de publication par défaut", "")
    )
    return end_date is None or end_date.date() >= date.today()


def _source_url(reference: str) -> str:
    return (
        "https://choisirleservicepublic.gouv.fr/"
        f"offre-emploi/?query={reference}"
    )


def collect_choisir_service_public_offers(
    client: httpx.Client | None = None,
) -> list[JobOfferCreate]:
    owns_client = client is None
    http_client = client or httpx.Client(
        timeout=120.0,
        follow_redirects=True,
    )
    offers: list[JobOfferCreate] = []

    try:
        with http_client.stream("GET", CSP_RESOURCE_URL) as response:
            response.raise_for_status()
            rows = csv.DictReader(response.iter_lines(), delimiter=";")
            for row in rows:
                if not _is_active(row):
                    continue
                title = row.get("Intitulé du poste", "")
                profession = row.get("Métier", "")
                specialization = row.get("Spécialisation", "")
                skills = row.get("Compétences attendues", "")
                contract = " ".join(
                    [
                        row.get("Nature de l'emploi", ""),
                        row.get("Nature de contrat", ""),
                        row.get("Durée du contrat", ""),
                    ]
                )
                if not is_target_offer(
                    title,
                    profession,
                    specialization,
                    skills,
                    contract,
                ):
                    continue
                reference = row.get("Référence", "").strip()
                description = "\n\n".join(
                    value.strip()
                    for value in (profession, specialization, skills)
                    if value.strip()
                )
                offers.append(
                    JobOfferCreate(
                        title=title.strip() or "Offre sans titre",
                        company=(
                            row.get("Employeur", "").strip()
                            or row.get("Organisme de rattachement", "").strip()
                            or "Employeur public"
                        ),
                        location=(
                            row.get("Lieu d'affectation", "").strip()
                            or row.get("Localisation du poste", "").strip()
                            or "France"
                        ),
                        contract_type=contract.strip() or "Alternance",
                        description=normalize_description(description),
                        source="Choisir le Service Public",
                        source_url=(
                            _source_url(reference) if reference else None
                        ),
                        published_at=_parse_date(
                            row.get("Date de première publication", "")
                        ),
                    )
                )
                if len(offers) >= MAX_RESULTS:
                    break
    except (httpx.HTTPError, csv.Error) as error:
        raise CollectorAPIError(
            "Choisir le Service Public request failed"
        ) from error
    finally:
        if owns_client:
            http_client.close()

    return offers
