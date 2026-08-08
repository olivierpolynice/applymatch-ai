from fastapi.testclient import TestClient


PROFILE_DATA = {
    "full_name": "Olivier Polynice",
    "education_level": "Bac+5",
    "program": "Master Réseaux, Cybersécurité et Cloud",
    "target_contract": "Alternance",
    "availability": "Septembre 2026",
    "work_schedule": "4 jours en entreprise",
    "location": "Île-de-France",
    "target_roles": (
        "Cybersécurité, Cloud, DevSecOps, Systèmes et Réseaux"
    ),
    "skills": (
        "Python, FastAPI, SQLAlchemy 2, PostgreSQL, Alembic et Docker"
    ),
}


def create_profile(client: TestClient) -> dict:
    response = client.post(
        "/candidate-profiles",
        json=PROFILE_DATA,
    )

    assert response.status_code == 201

    return response.json()


def test_create_candidate_profile(client: TestClient) -> None:
    response = client.post(
        "/candidate-profiles",
        json=PROFILE_DATA,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] == 1
    assert data["full_name"] == "Olivier Polynice"
    assert data["target_contract"] == "Alternance"
    assert data["is_active"] is True
    assert "created_at" in data
    assert "updated_at" in data


def test_get_candidate_profile(client: TestClient) -> None:
    created_profile = create_profile(client)

    response = client.get(
        f"/candidate-profiles/{created_profile['id']}"
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Olivier Polynice"


def test_update_candidate_profile(client: TestClient) -> None:
    created_profile = create_profile(client)

    new_skills = (
        "Python, FastAPI, Pytest, SQLAlchemy 2, PostgreSQL et Docker"
    )

    response = client.patch(
        f"/candidate-profiles/{created_profile['id']}",
        json={"skills": new_skills},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["skills"] == new_skills
    assert data["full_name"] == "Olivier Polynice"


def test_get_unknown_candidate_profile_returns_404(
    client: TestClient,
) -> None:
    response = client.get("/candidate-profiles/999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Candidate profile not found"
    }


def test_create_candidate_profile_with_invalid_data_returns_422(
    client: TestClient,
) -> None:
    invalid_profile = PROFILE_DATA.copy()
    invalid_profile["full_name"] = ""

    response = client.post(
        "/candidate-profiles",
        json=invalid_profile,
    )

    assert response.status_code == 422