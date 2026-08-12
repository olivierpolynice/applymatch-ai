from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import MatchResult
from tests.test_candidate_profiles import PROFILE_DATA
from tests.test_job_offers import OFFER_DATA


def create_profile(client: TestClient) -> dict:
    response = client.post(
        "/candidate-profiles",
        json=PROFILE_DATA,
    )

    assert response.status_code == 201
    return response.json()


def create_offer(client: TestClient) -> dict:
    response = client.post(
        "/job-offers",
        json=OFFER_DATA,
    )

    assert response.status_code == 201
    return response.json()


def test_match_profile_with_offer(client: TestClient) -> None:
    profile = create_profile(client)
    offer = create_offer(client)

    response = client.post(
        f"/matching/profile/{profile['id']}/offer/{offer['id']}"
    )

    assert response.status_code == 200

    data = response.json()

    assert 0 <= data["score"] <= 100
    assert data["recommendation"] in {
        "Excellente compatibilité",
        "Bonne compatibilité",
        "Compatibilité moyenne",
        "Compatibilité faible",
    }
    assert isinstance(data["matched_skills"], list)
    assert isinstance(data["missing_skills"], list)

    assert data["details"]["contract_match"] is True
    assert data["details"]["location_match"] is True
    assert data["details"]["contract_score"] == 10
    assert data["details"]["location_score"] == 10

    assert data["score"] == sum(
        [
            data["details"]["skills_score"],
            data["details"]["role_score"],
            data["details"]["contract_score"],
            data["details"]["location_score"],
        ]
    )


def test_matching_detects_expected_skills(
    client: TestClient,
) -> None:
    profile = create_profile(client)
    offer = create_offer(client)

    response = client.post(
        f"/matching/profile/{profile['id']}/offer/{offer['id']}"
    )

    assert response.status_code == 200

    data = response.json()

    assert "networking" in data["matched_skills"]
    assert "security" in data["matched_skills"]


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
        "https://example.com/jobs/cloud-devops-engineer"
    )
    offer_data["title"] = "Alternance Cloud DevOps Engineer"
    offer_data["description"] = (
        "Administration Linux avec Docker, Kubernetes, Terraform "
        "et Microsoft Azure pour sécuriser une infrastructure cloud."
    )

    offer_response = client.post(
        "/job-offers",
        json=offer_data,
    )

    assert offer_response.status_code == 201
    offer = offer_response.json()

    response = client.post(
        f"/matching/profile/{profile['id']}/offer/{offer['id']}"
    )

    assert response.status_code == 200

    data = response.json()

    assert "docker" in data["matched_skills"]
    assert "azure" in data["missing_skills"]
    assert "kubernetes" in data["missing_skills"]
    assert "terraform" in data["missing_skills"]


def test_matching_is_saved_and_updated(
    client: TestClient,
    db_session: Session,
) -> None:
    profile = create_profile(client)
    offer = create_offer(client)

    endpoint = (
        f"/matching/profile/{profile['id']}/offer/{offer['id']}"
    )

    first_response = client.post(endpoint)
    second_response = client.post(endpoint)

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    stored_count = db_session.scalar(
        select(func.count()).select_from(MatchResult)
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

    assert stored_result.score == response_data["score"]
    assert (
        stored_result.recommendation
        == response_data["recommendation"]
    )
    assert (
        stored_result.matched_skills
        == response_data["matched_skills"]
    )
    assert (
        stored_result.missing_skills
        == response_data["missing_skills"]
    )


def test_list_match_results_sorted_by_score(
    client: TestClient,
    db_session: Session,
) -> None:
    profile = create_profile(client)
    first_offer = create_offer(client)

    second_offer_data = OFFER_DATA.copy()
    second_offer_data["source_url"] = (
        "https://example.com/jobs/second-security-offer"
    )
    second_offer_data["title"] = (
        "Alternance Cloud Security Engineer"
    )

    second_offer_response = client.post(
        "/job-offers",
        json=second_offer_data,
    )

    assert second_offer_response.status_code == 201
    second_offer = second_offer_response.json()

    first_match_response = client.post(
        f"/matching/profile/{profile['id']}/offer/{first_offer['id']}"
    )
    second_match_response = client.post(
        f"/matching/profile/{profile['id']}/offer/{second_offer['id']}"
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
        f"/matching/profile/{profile['id']}/offer/{offer['id']}"
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
        "detail": "minimum_score must be between 0 and 100"
    }