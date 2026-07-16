from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.security import generate_api_key
from app.core.config import settings


client = TestClient(app)


def test_facility_search_and_detail_endpoints_work() -> None:
    listing = client.get("/api/v1/facilities", params={"query": "synthetic"})
    assert listing.status_code == 200
    payload = listing.json()
    assert payload["total"] >= 3
    facility_id = payload["items"][0]["id"]

    detail = client.get(f"/api/v1/facilities/{facility_id}")
    assert detail.status_code == 200
    assert detail.json()["facility"]["synthetic"] is True


def test_facility_evidence_and_sources_are_exposed() -> None:
    evidence = client.get("/api/v1/facilities/fac_syn_ashburn/evidence")
    assert evidence.status_code == 200
    assert evidence.json()["evidence"][0]["source_id"] == "src_syn_plan_ashburn"

    sources = client.get("/api/v1/facilities/fac_syn_ashburn/sources")
    assert sources.status_code == 200
    assert sources.json()["sources"][0]["reliability"]["score"] >= 80


def test_facility_estimate_includes_versions_and_assumptions() -> None:
    response = client.post("/api/v1/facilities/fac_syn_ashburn/estimate")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_water"]["expected_liters_per_hour"] > 0
    assert payload["model_versions"]["dataset_versions"]["facilityRegistry"] == "2026.07.1"
    assert payload["assumptions"]


def test_batch_and_compare_endpoints_work() -> None:
    batch = client.post(
        "/api/v1/facilities/estimate-batch",
        json={"facility_ids": ["fac_syn_ashburn", "fac_syn_dublin"]},
    )
    assert batch.status_code == 200
    assert len(batch.json()["results"]) == 2

    comparison = client.post(
        "/api/v1/facilities/compare",
        json={"facility_ids": ["fac_syn_ashburn", "fac_syn_dublin"]},
    )
    assert comparison.status_code == 200
    assert len(comparison.json()["rankings"]) == 2


def test_organization_and_source_endpoints_work() -> None:
    organizations = client.get("/api/v1/organizations")
    assert organizations.status_code == 200
    assert organizations.json()["total"] >= 2

    source = client.get("/api/v1/sources/src_syn_plan_ashburn")
    assert source.status_code == 200
    assert source.json()["source_type"] == "planning-application"


def test_corrections_and_ingestion_jobs_work() -> None:
    correction = client.post(
        "/api/v1/corrections",
        json={
            "facility_id": "fac_syn_ashburn",
            "field": "announcedItLoadMw",
            "proposed_value": "90",
            "source_url": "https://example.com/corrections/source.pdf",
            "notes": "Synthetic correction fixture"
        },
    )
    assert correction.status_code == 200
    assert correction.json()["status"] == "pending-review"

    job = client.post(
        "/api/v1/ingestion/jobs",
        json={
            "source_url": "https://example.com/docs/new-facility.pdf",
            "source_type": "planning-application",
            "dry_run": True,
        },
    )
    assert job.status_code == 200
    assert job.json()["status"] == "completed"


def test_unsafe_ingestion_url_is_rejected() -> None:
    response = client.post(
        "/api/v1/ingestion/jobs",
        json={
            "source_url": "http://localhost/private.pdf",
            "source_type": "planning-application",
            "dry_run": True,
        },
    )
    assert response.status_code == 400


def test_admin_review_endpoints_require_admin_key() -> None:
    forbidden = client.get("/api/v1/admin/review")
    assert forbidden.status_code == 403

    original_admin = settings.admin_api_key_hashes
    key, hashed = generate_api_key("aq_test_")
    settings.admin_api_key_hashes = [hashed]
    try:
        allowed = client.get("/api/v1/admin/review", headers={"X-API-Key": key})
        assert allowed.status_code == 200
        candidate_id = allowed.json()["items"][0]["id"]

        approve = client.post(f"/api/v1/admin/review/{candidate_id}/approve", headers={"X-API-Key": key})
        assert approve.status_code == 200
        assert approve.json()["status"] == "accepted"
    finally:
        settings.admin_api_key_hashes = original_admin


def test_phase3_schema_and_fixture_assets_exist() -> None:
    assert Path("schemas/facility-import.schema.json").exists()
    assert Path("schemas/candidate-fact.schema.json").exists()
    assert Path("schemas/source-record.schema.json").exists()
    assert Path("tests/fixtures/documents/synthetic-sustainability-report.txt").exists()
    assert Path("tests/fixtures/ingestion/source-job.json").exists()
