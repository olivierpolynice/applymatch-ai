import os
from typing import Any

import httpx

from app.schemas import JobOfferCreate
from app.services.collectors.ats_common import (
    clean_html,
    comma_separated_environment,
    is_target_offer,
    normalize_description,
    parse_datetime,
)
from app.services.collectors.la_bonne_alternance import (
    CollectorAPIError,
    CollectorConfigurationError,
)


SMARTRECRUITERS_URL = (
    "https://api.smartrecruiters.com/v1/companies/"
    "{company}/postings"
)


def _description(details: dict[str, Any]) -> str:
    sections = (details.get("jobAd") or {}).get("sections") or {}
    return clean_html(
        " ".join(
            str(section.get("text") or "")
            for section in sections.values()
            if isinstance(section, dict)
        )
    )


def collect_smartrecruiters_offers(
    client: httpx.Client | None = None,
) -> list[JobOfferCreate]:
    companies = comma_separated_environment(
        os.getenv("SMARTRECRUITERS_COMPANIES")
    )
    if not companies:
        raise CollectorConfigurationError(
            "SMARTRECRUITERS_COMPANIES is not configured"
        )

    owns_client = client is None
    http_client = client or httpx.Client(timeout=30.0)
    offers: list[JobOfferCreate] = []

    try:
        for company in companies:
            base_url = SMARTRECRUITERS_URL.format(company=company)
            try:
                response = http_client.get(
                    base_url,
                    params={"limit": 100, "country": "fr"},
                )
                response.raise_for_status()
                postings = response.json().get("content", [])
            except (httpx.HTTPError, ValueError) as error:
                raise CollectorAPIError(
                    f"SmartRecruiters request failed for {company}"
                ) from error

            for posting in postings:
                if not isinstance(posting, dict):
                    continue
                summary = " ".join(
                    str((posting.get(key) or {}).get("label") or "")
                    for key in (
                        "department",
                        "function",
                        "typeOfEmployment",
                    )
                )
                title = str(posting.get("name") or "Offre sans titre")
                if not is_target_offer(title, summary):
                    continue
                posting_id = posting.get("id") or posting.get("uuid")
                try:
                    detail_response = http_client.get(
                        f"{base_url}/{posting_id}"
                    )
                    detail_response.raise_for_status()
                    details = detail_response.json()
                except (httpx.HTTPError, ValueError) as error:
                    raise CollectorAPIError(
                        "SmartRecruiters detail request failed "
                        f"for {company}"
                    ) from error

                description = _description(details)
                if not is_target_offer(title, summary, description):
                    continue
                location = posting.get("location") or {}
                company_data = posting.get("company") or {}
                employment = posting.get("typeOfEmployment") or {}
                offers.append(
                    JobOfferCreate(
                        title=title.strip(),
                        company=str(
                            company_data.get("name") or company
                        ),
                        location=", ".join(
                            str(location.get(key) or "").strip()
                            for key in ("city", "region", "country")
                            if str(location.get(key) or "").strip()
                        ) or "Localisation non renseignée",
                        contract_type=str(
                            employment.get("label") or "Alternance"
                        ),
                        description=normalize_description(description),
                        source=f"SmartRecruiters - {company}",
                        source_url=details.get("applyUrl"),
                        published_at=parse_datetime(
                            posting.get("releasedDate")
                        ),
                    )
                )
    finally:
        if owns_client:
            http_client.close()

    return offers
