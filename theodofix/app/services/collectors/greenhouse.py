import os
from typing import Any

import httpx

from app.schemas import JobOfferCreate
from app.services.collectors.ats_common import (
    clean_html,
    comma_separated_environment,
    get_blocked_companies,
    is_blocked_company,
    is_target_offer,
    normalize_description,
    parse_datetime,
)
from app.services.collectors.la_bonne_alternance import (
    CollectorAPIError,
    CollectorConfigurationError,
)


GREENHOUSE_URL = (
    "https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
)


def collect_greenhouse_offers(
    client: httpx.Client | None = None,
) -> list[JobOfferCreate]:
    boards = comma_separated_environment(
        os.getenv("GREENHOUSE_BOARDS")
    )
    if not boards:
        raise CollectorConfigurationError(
            "GREENHOUSE_BOARDS is not configured"
        )

    owns_client = client is None
    http_client = client or httpx.Client(timeout=30.0)
    offers: list[JobOfferCreate] = []
    blocked_companies = get_blocked_companies()

    try:
        for board in boards:
            if is_blocked_company(board, blocked_companies):
                continue

            try:
                response = http_client.get(
                    GREENHOUSE_URL.format(board=board),
                    params={"content": "true"},
                )
                response.raise_for_status()
                jobs = response.json().get("jobs", [])
            except (httpx.HTTPError, ValueError) as error:
                raise CollectorAPIError(
                    f"Greenhouse request failed for {board}"
                ) from error

            for job in jobs:
                if not isinstance(job, dict):
                    continue
                title = str(job.get("title") or "Offre sans titre")
                content = clean_html(job.get("content"))
                metadata = " ".join(
                    str(item.get("value") or "")
                    for item in job.get("metadata") or []
                    if isinstance(item, dict)
                )
                if not is_target_offer(title, content, metadata):
                    continue
                location = job.get("location") or {}
                offers.append(
                    JobOfferCreate(
                        title=title.strip(),
                        company=board,
                        location=str(
                            location.get("name")
                            or "Localisation non renseignée"
                        ),
                        contract_type="Alternance",
                        description=normalize_description(content),
                        source=f"Greenhouse - {board}",
                        source_url=job.get("absolute_url"),
                        published_at=parse_datetime(job.get("updated_at")),
                    )
                )
    finally:
        if owns_client:
            http_client.close()

    return offers
