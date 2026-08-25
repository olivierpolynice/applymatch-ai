from pathlib import Path

from app.services.collector_scheduler import (
    CollectorSchedulerSettings,
    parse_interval_minutes,
)
from app.services.job_offers import build_offer_fingerprint


def test_scheduler_defaults_to_fifteen_minutes(
    monkeypatch,
) -> None:
    monkeypatch.delenv("COLLECTOR_INTERVAL_MINUTES", raising=False)
    monkeypatch.delenv("COLLECTOR_SCHEDULER_ENABLED", raising=False)
    monkeypatch.delenv("COLLECTOR_RUN_ON_STARTUP", raising=False)

    settings = CollectorSchedulerSettings.from_environment()

    assert settings.interval_minutes == 15
    assert settings.enabled is False
    assert settings.run_on_startup is False
    assert parse_interval_minutes("0") == 1


def test_fingerprint_prefers_source_and_external_id() -> None:
    first = build_offer_fingerprint(
        title="Alternance Python",
        company="Entreprise A",
        location="Paris",
        source="France Travail",
        external_id="FT-123",
        source_url="https://example.com/ancienne-url",
    )
    changed_metadata = build_offer_fingerprint(
        title="Nouveau titre",
        company="Nouvelle entreprise",
        location="Nanterre",
        source="France Travail",
        external_id="FT-123",
        source_url="https://example.com/nouvelle-url",
    )
    another_source = build_offer_fingerprint(
        title="Nouveau titre",
        company="Nouvelle entreprise",
        location="Nanterre",
        source="Jooble",
        external_id="FT-123",
    )

    assert first == changed_metadata
    assert first != another_source
    assert len(first) == 64


def test_fallback_fingerprint_uses_url() -> None:
    base = {
        "title": "Alternance Cloud",
        "company": "Entreprise Test",
        "location": "Paris",
        "source": "Jooble",
    }

    first = build_offer_fingerprint(
        **base,
        source_url="https://example.com/1",
    )
    second = build_offer_fingerprint(
        **base,
        source_url="https://example.com/2",
    )

    assert first != second
    assert len(first) == 64
    assert len(second) == 64


def test_environment_example_contains_phase5_variables() -> None:
    content = (
        Path(__file__).resolve().parents[1] / ".env.example"
    ).read_text(encoding="utf-8")

    for variable in (
        "FRANCE_TRAVAIL_CLIENT_ID=",
        "FRANCE_TRAVAIL_CLIENT_SECRET=",
        "COLLECTOR_INTERVAL_MINUTES=15",
    ):
        assert variable in content
