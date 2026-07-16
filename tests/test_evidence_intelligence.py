from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_facility_detail_exposes_primary_water_figure_and_contradictions() -> None:
    response = client.get("/api/v1/facilities/fac_syn_ashburn")
    assert response.status_code == 200
    payload = response.json()
    assert payload["primary_water_figure"]["evidence_class"] == "Level B"
    assert payload["primary_water_figure"]["figure_type"] == "official-permitted-maximum"
    assert payload["contradictory_claims"]


def test_estimate_response_distinguishes_modeled_result_from_official_figure() -> None:
    response = client.post("/api/v1/facilities/fac_syn_ashburn/estimate")
    assert response.status_code == 200
    payload = response.json()
    assert payload["result_classification"] == "modeled-estimate"
    assert payload["primary_water_figure"]["figure_type"] == "official-permitted-maximum"
    assert payload["source_evidence"][0]["evidence_class"].startswith("Level")


def test_source_summary_counts_independent_chains() -> None:
    response = client.get("/api/v1/facilities")
    assert response.status_code == 200
    item = next(entry for entry in response.json()["items"] if entry["id"] == "fac_syn_ashburn")
    assert item["source_summary"]["independent_chains"] >= 1
