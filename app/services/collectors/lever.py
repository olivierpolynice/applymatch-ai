import os

import httpx

from app.schemas import JobOfferCreate
from app.services.collectors.ats_common import (
    clean_html,
    comma_separated_environment,
    get_blocked_companies,
    is_blocked_company,
    is_target_offer,
    normalize_description,
)
from app.services.collectors.la_bonne_alternance import (
    CollectorAPIError,
    CollectorConfigurationError,
)


LEVER_URL = "https://api.lever.co/v0/postings/{site}"


def collect_lever_offers(
    client: httpx.Client | None = None,
) -> list[JobOfferCreate]:
    sites = comma_separated_environment(os.getenv("LEVER_SITES"))
    if not sites:
        raise CollectorConfigurationError(
            "LEVER_SITES is not configured"
        )

    owns_client = client is None
    http_client = client or httpx.Client(timeout=30.0)
    offers: list[JobOfferCreate] = []
    blocked_companies = get_blocked_companies()

    try:
        for site in sites:
            if is_blocked_company(site, blocked_companies):
                continue

            try:
                response = http_client.get(
                    LEVER_URL.format(site=site),
                    params={"mode": "json"},
                )
                response.raise_for_status()
                jobs = response.json()
            except (httpx.HTTPError, ValueError) as error:
                raise CollectorAPIError(
                    f"Lever request failed for {site}"
                ) from error

            if not isinstance(jobs, list):
                raise CollectorAPIError("Invalid Lever response")

            for job in jobs:
                if not isinstance(job, dict):
                    continue
                categories = job.get("categories") or {}
                title = str(job.get("text") or "Offre sans titre")
                description = clean_html(
                    " ".join(
                        [
                            str(job.get("descriptionPlain") or ""),
                            str(job.get("additionalPlain") or ""),
                        ]
                    )
                )
                commitment = str(categories.get("commitment") or "")
                if not is_target_offer(title, description, commitment):
                    continue
                offers.append(
                    JobOfferCreate(
                        title=title.strip(),
                        company=site,
                        location=str(
                            categories.get("location")
                            or "Localisation non renseignée"
                        ),
                        contract_type=commitment or "Alternance",
                        description=normalize_description(description),
                        source=f"Lever - {site}",
                        source_url=job.get("hostedUrl"),
                        published_at=None,
                    )
                )
    finally:
        if owns_client:
            http_client.close()

    return offers
