from app.services.collectors.ats_common import (
    is_blocked_company,
    is_target_offer,
    title_has_excluded_contract_keyword,
)


def test_title_with_cdi_is_excluded() -> None:
    assert title_has_excluded_contract_keyword(
        "Lead Fullstack Engineer - Secteur Public - CDI Paris - Theodo GovTech",
    )


def test_title_with_cdd_is_excluded() -> None:
    assert title_has_excluded_contract_keyword(
        "Ingenieur cloud - CDD 6 mois",
    )


def test_title_without_contract_keyword_is_not_excluded() -> None:
    assert not title_has_excluded_contract_keyword(
        "Technicien Informatique Systemes et Reseaux - Alternance",
    )


def test_is_target_offer_rejects_cdi_title_even_with_alternance_keyword() -> None:
    # Le mot "alternance" traine dans la description (mention generique de
    # l'entreprise) mais le titre annonce un CDI : l'offre doit etre rejetee.
    assert not is_target_offer(
        "Lead Product Manager - CDI Paris - Theodo",
        "Theodo propose aussi des postes en alternance dans d'autres equipes. "
        "Poste axe cloud et securite.",
        "CDI",
    )


def test_is_target_offer_accepts_real_alternance_offer() -> None:
    assert is_target_offer(
        "Alternance Technicien Informatique Systemes et Reseaux",
        "Administration systemes, reseau et securite au quotidien.",
        "Alternance",
    )


def test_is_blocked_company_is_case_and_accent_insensitive() -> None:
    blocked = {"theodo"}

    assert is_blocked_company("Theodo", blocked)
    assert is_blocked_company("THEODO", blocked)
    assert not is_blocked_company("Akuo", blocked)
