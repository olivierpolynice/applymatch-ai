from datetime import datetime, timedelta, timezone

import pytest

from app.models import CandidateProfile, JobOffer
from app.services.matching import calculate
from app.services.scoring_engine import (
    ScoreExplanation,
    decide_score,
    explain_score,
)


def build_profile() -> CandidateProfile:
    return CandidateProfile(
        full_name="Olivier Polynice",
        education_level="Bac+5",
        program="Master Réseaux, Cybersécurité et Cloud",
        target_contract="Alternance ou stage",
        availability="2026-09",
        work_schedule="4 jours en entreprise",
        location="Île-de-France, Paris",
        target_roles="Cybersécurité, Cloud, Réseaux, DevSecOps, IA",
        skills="Python, FastAPI, PostgreSQL, Docker",
        is_active=True,
    )


def build_offer(
    *,
    contract: str = "Alternance",
    age_hours: int = 2,
    experience_years: int = 2,
) -> JobOffer:
    return JobOffer(
        title=f"{contract} ingénieur cybersécurité Python",
        company="Entreprise Test",
        location="Paris 75001",
        contract_type=contract,
        description=(
            "Cybersécurité et Python obligatoires. "
            f"Expérience de {experience_years} ans. "
            "Formation Bac+5."
        ),
        source="test",
        source_url=None,
        fingerprint=(
            f"{contract}-{age_hours}-{experience_years}"
        ),
        status="new",
        published_at=(
            datetime.now(timezone.utc)
            - timedelta(hours=age_hours)
        ),
        experience_min=experience_years,
        experience_max=experience_years,
        application_status="not_started",
    )


@pytest.mark.parametrize(
    ("scenario", "expected_decision"),
    [
        ("alternance_conforme", "documents_ready"),
        ("stage_conforme", "documents_ready"),
        ("cdi_compatible", "rejected"),
        ("offre_25_heures", "rejected"),
        ("experience_3_ans", "rejected"),
        ("score_59", "manual_review"),
        ("score_60", "documents_ready"),
    ],
)
def test_decision_matrix(
    scenario: str,
    expected_decision: str,
) -> None:
    if scenario == "score_59":
        decision = decide_score(59, [])
    elif scenario == "score_60":
        decision = decide_score(60, [])
    else:
        offer_options = {
            "stage_conforme": {"contract": "Stage"},
            "cdi_compatible": {"contract": "CDI"},
            "offre_25_heures": {"age_hours": 25},
            "experience_3_ans": {"experience_years": 3},
        }.get(scenario, {})
        result = calculate(
            build_profile(),
            build_offer(**offer_options),
        )
        decision = result["decision"]

        if scenario == "cdi_compatible":
            assert result["score"] >= 60
            assert result["eligibility_reasons"]

    assert decision == expected_decision


def test_pydantic_score_explanation() -> None:
    explanation = explain_score(
        total_score=72,
        known_skills=["Python", "FastAPI"],
        unknown_skills=["Terraform"],
        blocking_reasons=[],
    )

    assert isinstance(explanation, ScoreExplanation)
    assert explanation.model_dump() == {
        "total_score": 72,
        "known_skills": ["Python", "FastAPI"],
        "unknown_skills": ["Terraform"],
        "blocking_reasons": [],
        "decision": "documents_ready",
    }
