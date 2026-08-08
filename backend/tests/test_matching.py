from fastapi.testclient import TestClient

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