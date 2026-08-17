import os
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import httpx

from app.schemas import JobOfferCreate
from app.services.collectors.ats_common import (
    clean_html,
    is_target_offer,
    normalize_description,
)
from app.services.collectors.la_bonne_alternance import (
    CollectorAPIError,
    CollectorConfigurationError,
)


def _text(item: ET.Element, name: str) -> str:
    node = item.find(name)
    return (node.text or "").strip() if node is not None else ""


def collect_emploi_territorial_offers(
    client: httpx.Client | None = None,
) -> list[JobOfferCreate]:
    rss_url = os.getenv("EMPLOI_TERRITORIAL_RSS_URL", "").strip()
    if not rss_url:
        raise CollectorConfigurationError(
            "EMPLOI_TERRITORIAL_RSS_URL is not configured"
        )

    owns_client = client is None
    http_client = client or httpx.Client(timeout=30.0)
    try:
        response = http_client.get(rss_url)
        response.raise_for_status()
        root = ET.fromstring(response.content)
    except (httpx.HTTPError, ET.ParseError) as error:
        raise CollectorAPIError(
            "Emploi Territorial RSS request failed"
        ) from error
    finally:
        if owns_client:
            http_client.close()

    offers: list[JobOfferCreate] = []
    for item in root.findall(".//item"):
        title = _text(item, "title")
        description = clean_html(_text(item, "description"))
        if not is_target_offer(title, description):
            continue
        published_at = None
        publication = _text(item, "pubDate")
        if publication:
            try:
                published_at = parsedate_to_datetime(publication)
            except (TypeError, ValueError):
                pass
        offers.append(
            JobOfferCreate(
                title=title or "Offre sans titre",
                company="Fonction publique territoriale",
                location="Île-de-France",
                contract_type="Alternance",
                description=normalize_description(description),
                source="Emploi Territorial",
                source_url=_text(item, "link") or None,
                published_at=published_at,
            )
        )
    return offers
