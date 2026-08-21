from pathlib import Path

import pytest

from app.services.profile_loader import load_profile
from app.services.technology_matcher import (
    analyze_technologies,
    normalize,
)


PROFILE_PATH = (
    Path(__file__).resolve().parents[1]
    / "candidate_profile"
    / "candidate_profile.yaml"
)


def test_profile_technologies_are_unique_and_have_evidence() -> None:
    document = load_profile(PROFILE_PATH)
    normalized_names = [
        normalize(technology.name)
        for technology in document.technologies
    ]

    assert document.technologies
    assert len(normalized_names) == len(set(normalized_names))
    assert all(
        technology.evidence
        for technology in document.technologies
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Postgres obligatoire", "PostgreSQL"),
        ("Développement en JS", "JavaScript"),
        ("API Python avec fast api", "FastAPI"),
        ("Déploiement avec docker-compose", "Docker Compose"),
    ],
)
def test_known_aliases_are_recognized(
    text: str,
    expected: str,
) -> None:
    analysis = analyze_technologies(text)

    assert expected in analysis.known
    assert expected not in analysis.unknown
    assert analysis.evidence[expected]


def test_small_typo_is_recognized_by_rapidfuzz() -> None:
    analysis = analyze_technologies(
        "Une expérience PostgreSQLl est demandée."
    )

    assert "PostgreSQL" in analysis.known


def test_unknown_required_and_preferred_technologies() -> None:
    analysis = analyze_technologies(
        "K8s est obligatoire. Terraform serait un plus. "
        "Microsoft Azure est requis."
    )

    assert set(analysis.unknown) >= {
        "Kubernetes",
        "Terraform",
        "Azure",
    }
    assert set(analysis.required) >= {"Kubernetes", "Azure"}
    assert "Terraform" in analysis.preferred


def test_short_aliases_do_not_create_fuzzy_false_positives() -> None:
    analysis = analyze_technologies(
        "Vous faites preuve d'aisance et de rigueur."
    )

    assert "Intelligence artificielle" not in analysis.known
    assert "JavaScript" not in analysis.known
