from fastapi.testclient import TestClient


OFFER_DATA = {
    "title": "Alternance Network & Security Administrator",
    "company": "Akuo",
    "location": "Paris",
    "contract_type": "Alternance",
    "description": (
        "Administration des rÃ©seaux, sÃ©curitÃ© des systÃ¨mes, support aux "
        "utilisateurs et participation aux projets de cybersÃ©curitÃ©."
    ),
    "source": "Import manuel",
    "source_url": "https://example.com/jobs/akuo-network-security",
    "published_at": None,
}


def create_offer(authenticated_client: TestClient) -> dict:
    response = authenticated_client.post(
        "/job-offers",
        json=OFFER_DATA,
    )

    assert response.status_code == 201

    return response.json()


def test_create_job_offer(authenticated_client: TestClient) -> None:
    response = authenticated_client.post(
        "/job-offers",
        json=OFFER_DATA,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] == 1
    assert data["title"] == OFFER_DATA["title"]
    assert data["company"] == "Akuo"
    assert data["status"] == "new"
    assert "created_at" in data
    assert "updated_at" in data


def test_list_job_offers(authenticated_client: TestClient) -> None:
    created_offer = create_offer(authenticated_client)

    response = authenticated_client.get("/job-offers")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == created_offer["id"]
    assert data[0]["company"] == "Akuo"


def test_filter_job_offers_by_status(
    authenticated_client: TestClient,
) -> None:
    create_offer(authenticated_client)

    response = authenticated_client.get(
        "/job-offers",
        params={"status": "new"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1

    empty_response = authenticated_client.get(
        "/job-offers",
        params={"status": "saved"},
    )

    assert empty_response.status_code == 200
    assert empty_response.json() == []


def test_get_job_offer(authenticated_client: TestClient) -> None:
    created_offer = create_offer(authenticated_client)

    response = authenticated_client.get(
        f"/job-offers/{created_offer['id']}",
    )

    assert response.status_code == 200
    assert response.json()["title"] == OFFER_DATA["title"]


def test_update_job_offer_status(
    authenticated_client: TestClient,
) -> None:
    created_offer = create_offer(authenticated_client)

    response = authenticated_client.patch(
        f"/job-offers/{created_offer['id']}",
        json={"status": "saved"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "saved"
    assert response.json()["title"] == OFFER_DATA["title"]


def test_mark_job_offer_as_applied(
    authenticated_client: TestClient,
) -> None:
    created_offer = create_offer(authenticated_client)

    response = authenticated_client.post(
        f"/job-offers/{created_offer['id']}/mark-applied",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "applied"
    assert data["applied_at"] is not None

    history_response = authenticated_client.get(
        "/job-offers",
        params={"status": "applied"},
    )

    assert history_response.status_code == 200
    assert len(history_response.json()) == 1
    assert history_response.json()[0]["id"] == (
        created_offer["id"]
    )


def test_mark_applied_requires_authentication(
    client: TestClient,
) -> None:
    response = client.post(
        "/job-offers/1/mark-applied",
    )

    assert response.status_code == 401


def test_mark_applied_twice_is_rejected(
    authenticated_client: TestClient,
) -> None:
    created_offer = create_offer(authenticated_client)
    path = (
        f"/job-offers/{created_offer['id']}"
        "/mark-applied"
    )

    first_response = authenticated_client.post(path)
    second_response = authenticated_client.post(path)

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": (
            "Job offer is already marked as applied"
        )
    }


def test_mark_unknown_offer_as_applied_returns_404(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.post(
        "/job-offers/999/mark-applied",
    )

    assert response.status_code == 404


def test_duplicate_source_url_returns_409(
    authenticated_client: TestClient,
) -> None:
    create_offer(authenticated_client)

    response = authenticated_client.post(
        "/job-offers",
        json=OFFER_DATA,
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "A job offer with this source URL already exists"
        )
    }


def test_unknown_job_offer_returns_404(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.get("/job-offers/999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Job offer not found"
    }


def test_invalid_job_offer_returns_422(
    authenticated_client: TestClient,
) -> None:
    invalid_offer = OFFER_DATA.copy()
    invalid_offer["description"] = "court"

    response = authenticated_client.post(
        "/job-offers",
        json=invalid_offer,
    )

    assert response.status_code == 422


def test_create_job_offer_without_source_url(
    authenticated_client: TestClient,
) -> None:
    offer_without_url = OFFER_DATA.copy()
    offer_without_url["source_url"] = None

    response = authenticated_client.post(
        "/job-offers",
        json=offer_without_url,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["source_url"] is None
    assert data["title"] == OFFER_DATA["title"]
    assert data["company"] == "Akuo"


def test_duplicate_offer_without_url_returns_409(
    authenticated_client: TestClient,
) -> None:
    first_offer = OFFER_DATA.copy()
    first_offer["source_url"] = None

    second_offer = first_offer.copy()
    second_offer["title"] = (
        "  ALTERNANCE Network & Security Administrator  "
    )
    second_offer["company"] = " AKUO "
    second_offer["location"] = "  PARIS "

    first_response = authenticated_client.post(
        "/job-offers",
        json=first_offer,
    )
    second_response = authenticated_client.post(
        "/job-offers",
        json=second_offer,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": "This job offer already exists"
    }


def test_delete_job_offers_by_company_is_case_insensitive(
    authenticated_client: TestClient,
) -> None:
    theodo_offer = OFFER_DATA.copy()
    theodo_offer["company"] = "theodo"
    theodo_offer["source_url"] = "https://example.com/jobs/theodo-1"

    other_offer = OFFER_DATA.copy()
    other_offer["company"] = "Akuo"
    other_offer["source_url"] = "https://example.com/jobs/akuo-2"

    authenticated_client.post("/job-offers", json=theodo_offer)
    authenticated_client.post("/job-offers", json=other_offer)

    response = authenticated_client.delete(
        "/job-offers/by-company/THEODO",
    )

    assert response.status_code == 200
    assert response.json() == {"deleted": 1}

    remaining = authenticated_client.get("/job-offers").json()

    assert len(remaining) == 1
    assert remaining[0]["company"] == "Akuo"


def test_delete_job_offers_by_company_with_no_match(
    authenticated_client: TestClient,
) -> None:
    create_offer(authenticated_client)

    response = authenticated_client.delete(
        "/job-offers/by-company/entreprise-inconnue",
    )

    assert response.status_code == 200
    assert response.json() == {"deleted": 0}

    remaining = authenticated_client.get("/job-offers").json()

    assert len(remaining) == 1
