import csv
import logging
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


logger = logging.getLogger(__name__)

CSP_RESOURCE_URL = (
    "https://www.data.gouv.fr/api/1/datasets/r/"
    "867034a2-2fa1-41b4-bd39-c84691ea618f"
)
MAX_RESULTS = 200
PARIS_TIMEZONE = ZoneInfo("Europe/Paris")


def _field(row: dict[str, str], key: str) -> str:
    # csv.DictReader met la valeur à None (pas "") pour une colonne
    # manquante quand une ligne a moins de champs que l'en-tête :
    # row.get(key, "") renvoie alors None (la clé existe, avec une
    # valeur None), pas la valeur par défaut "". On sécurise ici pour ne
    # jamais planter sur un .strip() plus loin dans ce fichier.
    return (row.get(key) or "").strip()


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None

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
        row.get("Date de fin de publication par défaut")
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
    skipped_rows = 0

    try:
        with http_client.stream("GET", CSP_RESOURCE_URL) as response:
            response.raise_for_status()
            rows = csv.DictReader(response.iter_lines(), delimiter=";")
            for row in rows:
                try:
                    if not _is_active(row):
                        continue

                    title = _field(row, "Intitulé du poste")
                    profession = _field(row, "Métier")
                    specialization = _field(row, "Spécialisation")
                    skills = _field(row, "Compétences attendues")
                    contract = " ".join(
                        part
                        for part in (
                            _field(row, "Nature de l'emploi"),
                            _field(row, "Nature de contrat"),
                            _field(row, "Durée du contrat"),
                        )
                        if part
                    )

                    if not is_target_offer(
                        title,
                        profession,
                        specialization,
                        skills,
                        contract,
                    ):
                        continue

                    reference = _field(row, "Référence")
                    description = "\n\n".join(
                        value
                        for value in (profession, specialization, skills)
                        if value
                    )

                    offers.append(
                        JobOfferCreate(
                            title=title or "Offre sans titre",
                            company=(
                                _field(row, "Employeur")
                                or _field(
                                    row,
                                    "Organisme de rattachement",
                                )
                                or "Employeur public"
                            ),
                            location=(
                                _field(row, "Lieu d'affectation")
                                or _field(
                                    row,
                                    "Localisation du poste",
                                )
                                or "France"
                            ),
                            contract_type=contract or "Alternance",
                            description=normalize_description(
                                description
                            ),
                            source="Choisir le Service Public",
                            source_url=(
                                _source_url(reference)
                                if reference
                                else None
                            ),
                            published_at=_parse_date(
                                row.get(
                                    "Date de première publication"
                                )
                            ),
                        )
                    )

                    if len(offers) >= MAX_RESULTS:
                        break
                except Exception:
                    # Une ligne du CSV mal formée (colonnes manquantes,
                    # encodage inattendu...) ne doit pas faire échouer
                    # toute la collecte : on la saute et on continue
                    # avec les lignes suivantes.
                    skipped_rows += 1
                    continue
    except (httpx.HTTPError, csv.Error) as error:
        raise CollectorAPIError(
            "Choisir le Service Public request failed"
        ) from error
    finally:
        if owns_client:
            http_client.close()

    if skipped_rows:
        logger.warning(
            "Choisir le Service Public : %s ligne(s) CSV "
            "ignorée(s) (format inattendu).",
            skipped_rows,
        )

    return offers
