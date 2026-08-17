from fastapi.testclient import TestClient


PROFILE_DATA = {
    "full_name": "Olivier Polynice",
    "education_level": "Bac+5",
    "program": "Master RÃ©seaux, CybersÃ©curitÃ© & Cloud",
    "target_contract": "Alternance",
    "availability": "Septembre 2026",
    "work_schedule": "4 jours en entreprise",
    "location": "ÃŽle-de-France",
    "target_roles": (
        "CybersÃ©curitÃ©, administration systÃ¨mes et rÃ©seaux, "
        "cloud, DevSecOps"
    ),
    "skills": (
        "Python, FastAPI, React, TypeScript, Docker, Linux, "
        "GitHub Actions, networking, security, cloud, RBAC, JWT"
    ),
}


OFFER_DATA = {
    "title": "Alternance Network & Security Administrator",
    "company": "Entreprise Demo",
    "location": "Paris, ÃŽle-de-France",
    "contract_type": "Alternance",
    "description": (
        "Administration des systÃ¨mes et rÃ©seaux, sÃ©curisation des "
        "infrastructures, supervision, Linux, Docker, cloud, "
        "networking et gestion des incidents de sÃ©curitÃ©."
    ),
    "source": "ApplyMatch Demo",
    "source_url": (
        "https://example.com/jobs/"
        "network-security-administrator-demo"
    ),
    "published_at": None,
}


def test_complete_demo_workflow(authenticated_client: TestClient) -> None:
    profile_response = authenticated_client.post(
        "/candidate-profiles",
        json=PROFILE_DATA,
    )

    assert profile_response.status_code == 201
    profile = profile_response.json()

    assert profile["full_name"] == "Olivier Polynice"
    assert profile["is_active"] is True

    offer_response = authenticated_client.post(
        "/job-offers",
        json=OFFER_DATA,
    )

    assert offer_response.status_code == 201
    offer = offer_response.json()

    assert offer["title"] == OFFER_DATA["title"]
    assert offer["status"] == "new"

    matching_response = authenticated_client.post(
        f"/matching/profile/{profile['id']}/offer/{offer['id']}"
    )

    assert matching_response.status_code == 200
    matching = matching_response.json()

    assert 0 <= matching["score"] <= 100
    assert matching["recommendation"]
    assert isinstance(matching["matched_skills"], list)
    assert isinstance(matching["missing_skills"], list)

    results_response = authenticated_client.get(
        f"/matching/profile/{profile['id']}/results"
    )

    assert results_response.status_code == 200

    results = results_response.json()

    assert len(results) == 1
    assert results[0]["profile_id"] == profile["id"]
    assert results[0]["offer_id"] == offer["id"]
    assert results[0]["score"] == matching["score"]
