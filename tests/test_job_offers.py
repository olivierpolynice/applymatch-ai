from fastapi.testclient import TestClient


OFFER_DATA = {
    "title": "Alternance Network & Security Administrator",
    "company": "Akuo",
    "location": "Paris",
    "contract_type": "Alternance",
    "description": (
        "Administration des réseaux, sécurité des systèmes, support aux "
        "utilisateurs et participation aux projets de cybersécurité."
    ),
    "source": "Import manuel",
    "source_url": "https://example.com/jobs/akuo-network-security",
    "published_at": "2026-08-08T12:00:00+02:00",
}


def create_offer(client: TestClient) -> dict:
    response = client.post("/job-offers", json=OFFER_DATA)

    assert response.status_code == 201

    return response.json()


def test_create_job_offer(client: TestClient) -> None:
    response = client.post("/job-offers", json=OFFER_DATA)

    assert response.status_code == 201

    data = response.json()

    assert data["id"] == 1
    assert data["title"] == OFFER_DATA["title"]
    assert data["company"] == "Akuo"
    assert data["status"] == "new"
    assert "created_at" in data
    assert "updated_at" in data


def test_list_job_offers(client: TestClient) -> None:
    created_offer = create_offer(client)

    response = client.get("/job-offers")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == created_offer["id"]
    assert data[0]["company"] == "Akuo"


def test_filter_job_offers_by_status(client: TestClient) -> None:
    create_offer(client)

    response = client.get("/job-offers", params={"status": "new"})

    assert response.status_code == 200
    assert len(response.json()) == 1

    empty_response = client.get(
        "/job-offers",
        params={"status": "saved"},
    )

    assert empty_response.status_code == 200
    assert empty_response.json() == []


def test_get_job_offer(client: TestClient) -> None:
    created_offer = create_offer(client)

    response = client.get(f"/job-offers/{created_offer['id']}")

    assert response.status_code == 200
    assert response.json()["title"] == OFFER_DATA["title"]


def test_update_job_offer_status(client: TestClient) -> None:
    created_offer = create_offer(client)

    response = client.patch(
        f"/job-offers/{created_offer['id']}",
        json={"status": "saved"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "saved"
    assert response.json()["title"] == OFFER_DATA["title"]


def test_duplicate_source_url_returns_409(
    client: TestClient,
) -> None:
    create_offer(client)

    response = client.post("/job-offers", json=OFFER_DATA)

    assert response.status_code == 409
    assert response.json() == {
        "detail": "A job offer with this source URL already exists"
    }


def test_unknown_job_offer_returns_404(
    client: TestClient,
) -> None:
    response = client.get("/job-offers/999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Job offer not found"
    }


def test_invalid_job_offer_returns_422(
    client: TestClient,
) -> None:
    invalid_offer = OFFER_DATA.copy()
    invalid_offer["description"] = "court"

    response = client.post("/job-offers", json=invalid_offer)

    assert response.status_code == 422