from app.services.ai_text_generation import enhance_application_texts
from app.services.application_drafts import build_cover_letter
from tests.test_scoring_engine_v3 import build_offer, build_profile


class MatchStub:
    known_technologies = ["Python"]
    unknown_technologies = ["Terraform"]
    matched_skills = ["python"]


def test_jinja_letter_has_stable_sections() -> None:
    profile = build_profile()
    offer = build_offer()
    letter = build_cover_letter(profile, offer, MatchStub())

    assert letter.startswith("Objet : Candidature")
    assert "Madame, Monsieur" in letter
    assert offer.company in letter
    assert offer.title in letter
    assert "Python" in letter
    assert letter.endswith(profile.full_name)


def test_ai_disabled_keeps_deterministic_texts(monkeypatch) -> None:
    monkeypatch.setenv("AI_TEXT_GENERATION_ENABLED", "false")
    profile = build_profile()
    offer = build_offer()

    letter, message = enhance_application_texts(
        profile=profile,
        offer=offer,
        match_result=MatchStub(),
        fallback_cover_letter="Lettre déterministe complète",
        fallback_short_message="Message déterministe",
    )

    assert letter == "Lettre déterministe complète"
    assert message == "Message déterministe"
