from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_public_record_templates_are_lawful_and_facility_specific() -> None:
    response = client.get("/api/v1/facilities/fac_syn_ashburn/public-records/templates")
    assert response.status_code == 200
    payload = response.json()
    assert payload["known_holders"]
    assert payload["templates"][0]["facility_id"] == "fac_syn_ashburn"
    assert "non-personal" in payload["templates"][0]["body"].lower()


def test_source_connector_registry_is_available() -> None:
    response = client.get("/api/v1/sources/connectors")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert payload["items"][0]["access_method"]
