from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import MatchResult
from app.services.matching import build_recommendations
from tests.test_candidate_profiles import PROFILE_DATA
from tests.test_job_offers import OFFER_DATA


def create_profile(
    client: TestClient,
    profile_data: dict | None = None,
) -> dict:
    response = client.post(
        "/candidate-profiles",
        json=profile_data or PROFILE_DATA,
    )

    assert response.status_code == 201

    return response.json()


def create_offer(
    client: TestClient,
    offer_data: dict | None = None,
) -> dict:
    response = client.post(
        "/job-offers",
        json=offer_data or OFFER_DATA,
    )

    assert response.status_code == 201

    return response.json()


def test_match_profile_with_offer(
    client: TestClient,
) -> None:
    profile = create_profile(client)
    offer = create_offer(client)

    response = client.post(
        f"/matching/profile/{profile['id']}"
        f"/offer/{offer['id']}"
    )

    assert response.status_code == 200

    data = response.json()
    details = data["details"]

    assert 0 <= data["score"] <= 100
    assert data["recommendation"] in {
        "Excellente compatibilité",
        "Bonne compatibilité",
        "Compatibilité moyenne",
        "Compatibilité faible",
    }
    assert data["confidence"] in {
        "élevée",
        "moyenne",
        "faible",
    }

    assert isinstance(
        data["matched_skills"],
        list,
    )
    assert isinstance(
        data["skills_to_strengthen"],
        list,
    )
    assert isinstance(
        data["missing_skills"],
        list,
    )

    assert details["contract_match"] is True
    assert details["location_match"] is True
    assert details["education_match"] is True

    assert details["contract_score"] == 15
    assert details["location_score"] == 10
    assert details["education_score"] == 5

    assert 0 <= details["skills_score"] <= 45
    assert details["role_score"] in {
        0,
        25,
    }

    assert data["score"] == sum(
        [
            details["skills_score"],
            details["role_score"],
            details["contract_score"],
            details["location_score"],
            details["education_score"],
        ]
    )


def test_matching_detects_expected_skills(
    client: TestClient,
) -> None:
    profile = create_profile(client)
    offer = create_offer(client)

    response = client.post(
        f"/matching/profile/{profile['id']}"
        f"/offer/{offer['id']}"
    )

    assert response.status_code == 200

    data = response.json()

    assert "networking" in data["matched_skills"]
    assert "security" in data["matched_skills"]


def test_matching_classifies_beginner_skills(
    client: TestClient,
) -> None:
    profile_data = PROFILE_DATA.copy()
    profile_data["skills"] = (
        f"{PROFILE_DATA['skills']}, "
        "Kubernetes (notions), "
        "Terraform (notions)"
    )

    profile = create_profile(
        client,
        profile_data,
    )

    offer_data = OFFER_DATA.copy()
    offer_data["source_url"] = (
        "https://example.com/jobs/"
        "cloud-kubernetes-terraform"
    )
    offer_data["title"] = (
        "Alternance Cloud DevSecOps"
    )
    offer_data["description"] = (
        "Vous participerez à la sécurisation d'une "
        "infrastructure cloud avec Kubernetes et Terraform. "
        "Vous travaillerez également avec Docker et Linux."
    )

    offer = create_offer(
        client,
        offer_data,
    )

    response = client.post(
        f"/matching/profile/{profile['id']}"
        f"/offer/{offer['id']}"
    )

    assert response.status_code == 200

    data = response.json()

    assert "kubernetes" in (
        data["skills_to_strengthen"]
    )
    assert "terraform" in (
        data["skills_to_strengthen"]
    )

    assert "kubernetes" not in (
        data["missing_skills"]
    )
    assert "terraform" not in (
        data["missing_skills"]
    )


def test_matching_detects_ai_skills(
    client: TestClient,
) -> None:
    profile_data = PROFILE_DATA.copy()
    profile_data["target_roles"] = (
        f"{PROFILE_DATA['target_roles']}, "
        "Intelligence artificielle"
    )
    profile_data["skills"] = (
        f"{PROFILE_DATA['skills']}, "
        "Python, Machine Learning"
    )

    profile = create_profile(
        client,
        profile_data,
    )

    offer_data = OFFER_DATA.copy()
    offer_data["source_url"] = (
        "https://example.com/jobs/"
        "machine-learning-engineer"
    )
    offer_data["title"] = (
        "Alternance Machine Learning Engineer"
    )
    offer_data["description"] = (
        "Vous développerez des modèles de machine learning "
        "en Python et participerez à des projets "
        "d'intelligence artificielle et de MLOps."
    )

    offer = create_offer(
        client,
        offer_data,
    )

    response = client.post(
        f"/matching/profile/{profile['id']}"
        f"/offer/{offer['id']}"
    )

    assert response.status_code == 200

    data = response.json()

    assert "machine learning" in (
        data["matched_skills"]
    )
    assert "python" in data["matched_skills"]
    assert data["details"]["role_match"] is True
    assert data["details"]["role_score"] == 25


def test_matching_unknown_profile_returns_404(
    client: TestClient,
) -> None:
    offer = create_offer(client)

    response = client.post(
        f"/matching/profile/999/offer/{offer['id']}"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Candidate profile not found"
    }


def test_matching_unknown_offer_returns_404(
    client: TestClient,
) -> None:
    profile = create_profile(client)

    response = client.post(
        f"/matching/profile/{profile['id']}/offer/999"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Job offer not found"
    }


def test_matching_with_missing_skill(
    client: TestClient,
) -> None:
    profile = create_profile(client)

    offer_data = OFFER_DATA.copy()
    offer_data["source_url"] = (
        "https://example.com/jobs/"
        "cloud-devops-engineer"
    )
    offer_data["title"] = (
        "Alternance Cloud DevOps Engineer"
    )
    offer_data["description"] = (
        "Administration Linux avec Docker, Kubernetes, "
        "Terraform et Microsoft Azure pour sécuriser "
        "une infrastructure cloud."
    )

    offer = create_offer(
        client,
        offer_data,
    )

    response = client.post(
        f"/matching/profile/{profile['id']}"
        f"/offer/{offer['id']}"
    )

    assert response.status_code == 200

    data = response.json()

    assert "docker" in data["matched_skills"]
    assert "azure" in data["missing_skills"]
    assert "kubernetes" in data["missing_skills"]
    assert "terraform" in data["missing_skills"]


def test_matching_handles_ile_de_france_department(
    client: TestClient,
) -> None:
    profile = create_profile(client)

    offer_data = OFFER_DATA.copy()
    offer_data["source_url"] = (
        "https://example.com/jobs/"
        "security-hauts-de-seine"
    )
    offer_data["location"] = (
        "12 rue Exemple 92000 Nanterre"
    )

    offer = create_offer(
        client,
        offer_data,
    )

    response = client.post(
        f"/matching/profile/{profile['id']}"
        f"/offer/{offer['id']}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["details"]["location_match"] is True
    assert data["details"]["location_score"] == 10


def test_matching_is_saved_and_updated(
    client: TestClient,
    db_session: Session,
) -> None:
    profile = create_profile(client)
    offer = create_offer(client)

    endpoint = (
        f"/matching/profile/{profile['id']}"
        f"/offer/{offer['id']}"
    )

    first_response = client.post(endpoint)
    second_response = client.post(endpoint)

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    stored_count = db_session.scalar(
        select(func.count()).select_from(
            MatchResult
        )
    )

    assert stored_count == 1

    stored_result = db_session.scalar(
        select(MatchResult).where(
            MatchResult.profile_id == profile["id"],
            MatchResult.offer_id == offer["id"],
        )
    )

    assert stored_result is not None

    response_data = second_response.json()

    assert stored_result.score == (
        response_data["score"]
    )
    assert stored_result.recommendation == (
        response_data["recommendation"]
    )
    assert stored_result.confidence == (
        response_data["confidence"]
    )
    assert stored_result.matched_skills == (
        response_data["matched_skills"]
    )
    assert stored_result.skills_to_strengthen == (
        response_data["skills_to_strengthen"]
    )
    assert stored_result.missing_skills == (
        response_data["missing_skills"]
    )


def test_list_match_results_sorted_by_score(
    client: TestClient,
    db_session: Session,
) -> None:
    profile = create_profile(client)
    first_offer = create_offer(client)

    second_offer_data = OFFER_DATA.copy()
    second_offer_data["source_url"] = (
        "https://example.com/jobs/"
        "second-security-offer"
    )
    second_offer_data["title"] = (
        "Alternance Cloud Security Engineer"
    )

    second_offer = create_offer(
        client,
        second_offer_data,
    )

    first_match_response = client.post(
        f"/matching/profile/{profile['id']}"
        f"/offer/{first_offer['id']}"
    )
    second_match_response = client.post(
        f"/matching/profile/{profile['id']}"
        f"/offer/{second_offer['id']}"
    )

    assert first_match_response.status_code == 200
    assert second_match_response.status_code == 200

    first_result = db_session.scalar(
        select(MatchResult).where(
            MatchResult.offer_id == first_offer["id"]
        )
    )
    second_result = db_session.scalar(
        select(MatchResult).where(
            MatchResult.offer_id == second_offer["id"]
        )
    )

    assert first_result is not None
    assert second_result is not None

    first_result.score = 60
    second_result.score = 90
    db_session.commit()

    response = client.get(
        f"/matching/profile/{profile['id']}/results"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert data[0]["score"] == 90
    assert data[0]["offer_id"] == second_offer["id"]
    assert data[1]["score"] == 60
    assert data[1]["offer_id"] == first_offer["id"]


def test_list_match_results_filters_minimum_score(
    client: TestClient,
    db_session: Session,
) -> None:
    profile = create_profile(client)
    offer = create_offer(client)

    match_response = client.post(
        f"/matching/profile/{profile['id']}"
        f"/offer/{offer['id']}"
    )

    assert match_response.status_code == 200

    stored_result = db_session.scalar(
        select(MatchResult).where(
            MatchResult.profile_id == profile["id"],
            MatchResult.offer_id == offer["id"],
        )
    )

    assert stored_result is not None

    stored_result.score = 65
    db_session.commit()

    included_response = client.get(
        f"/matching/profile/{profile['id']}/results"
        "?minimum_score=60"
    )
    excluded_response = client.get(
        f"/matching/profile/{profile['id']}/results"
        "?minimum_score=70"
    )

    assert included_response.status_code == 200
    assert len(included_response.json()) == 1

    assert excluded_response.status_code == 200
    assert excluded_response.json() == []


def test_list_match_results_rejects_invalid_requests(
    client: TestClient,
) -> None:
    unknown_profile_response = client.get(
        "/matching/profile/999/results"
    )

    assert unknown_profile_response.status_code == 404
    assert unknown_profile_response.json() == {
        "detail": "Candidate profile not found"
    }

    profile = create_profile(client)

    invalid_score_response = client.get(
        f"/matching/profile/{profile['id']}/results"
        "?minimum_score=101"
    )

    assert invalid_score_response.status_code == 422
    assert invalid_score_response.json() == {
        "detail": (
            "minimum_score must be between 0 and 100"
        )
    }
def test_recommendations_for_high_score() -> None:
    decision, priority, actions = build_recommendations(
        score=85,
        matched_skills=[
            "cloud",
            "python",
            "security",
        ],
        skills_to_strengthen=[
            "kubernetes",
            "terraform",
        ],
        missing_skills=[],
        role_match=True,
        contract_match=True,
        location_match=True,
        education_match=True,
    )

    assert decision == "recommended"
    assert priority == "high"
    assert any(
        "Candidature recommandée" in action
        for action in actions
    )
    assert any(
        "cloud, python, security" in action
        for action in actions
    )
    assert any(
        "kubernetes, terraform" in action
        for action in actions
    )


def test_recommendations_for_medium_score() -> None:
    decision, priority, actions = build_recommendations(
        score=60,
        matched_skills=["python"],
        skills_to_strengthen=[],
        missing_skills=[
            "azure",
            "kubernetes",
            "terraform",
            "ansible",
        ],
        role_match=True,
        contract_match=True,
        location_match=True,
        education_match=True,
    )

    assert decision == "consider"
    assert priority == "medium"
    assert any(
        "Candidature possible" in action
        for action in actions
    )
    assert any(
        "azure, kubernetes, terraform" in action
        for action in actions
    )
    assert all(
        "ansible" not in action
        for action in actions
    )


def test_recommendations_for_low_score() -> None:
    decision, priority, actions = build_recommendations(
        score=30,
        matched_skills=[],
        skills_to_strengthen=[],
        missing_skills=[],
        role_match=False,
        contract_match=False,
        location_match=False,
        education_match=False,
    )

    assert decision == "skip"
    assert priority == "low"
    assert any(
        "Ne pas prioriser" in action
        for action in actions
    )
    assert any(
        "type de contrat" in action
        for action in actions
    )
    assert any(
        "localisation" in action
        for action in actions
    )
    assert any(
        "niveau d’études" in action
        for action in actions
    )