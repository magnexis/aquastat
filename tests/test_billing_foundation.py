from fastapi.testclient import TestClient

from app.main import app
from app.security import generate_api_key
from app.services.ops_center import managed_key_store


client = TestClient(app)


def test_billing_packages_endpoint_lists_defaults() -> None:
    response = client.get("/api/v1/billing/packages")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 3
    assert payload["items"][0]["slug"] == "starter-refill"


def test_checkout_session_and_quota_summary_for_managed_key() -> None:
    _, _ = generate_api_key("aq_test_")
    created = client.post(
        "/api/v1/control-center/api-keys",
        headers={},
        json={
            "name": "billing key",
            "description": "billing foundation test",
            "environment": "testing",
            "scopes": ["calculations:read"],
            "allowed_endpoints": ["/api/v1/estimate"],
            "allowed_origins": [],
            "allowed_ips": [],
            "usage_limit": 1000,
        },
    )
    if created.status_code != 200:
        admin_key, admin_hash = generate_api_key("aq_test_")
        from app.core.config import settings

        original_admin = settings.admin_api_key_hashes
        settings.admin_api_key_hashes = [admin_hash]
        try:
            created = client.post(
                "/api/v1/control-center/api-keys",
                headers={"X-API-Key": admin_key},
                json={
                    "name": "billing key",
                    "description": "billing foundation test",
                    "environment": "testing",
                    "scopes": ["calculations:read"],
                    "allowed_endpoints": ["/api/v1/estimate"],
                    "allowed_origins": [],
                    "allowed_ips": [],
                    "usage_limit": 1000,
                },
            )
        finally:
            settings.admin_api_key_hashes = original_admin

    assert created.status_code == 200
    key_record = created.json()["record"]
    checkout = client.post(
        "/api/v1/billing/checkout-sessions",
        json={"package_slug": "starter-refill", "target_api_key_id": key_record["id"], "client_request_id": "cli-1"},
    )
    assert checkout.status_code == 200
    checkout_payload = checkout.json()
    assert checkout_payload["package_slug"] == "starter-refill"
    assert checkout_payload["target_api_key_prefix"] == key_record["prefix"]

    summary = client.get(f"/api/v1/billing/quota/{key_record['id']}")
    assert summary.status_code == 200
    summary_payload = summary.json()
    assert summary_payload["api_key_id"] == key_record["id"]
    assert summary_payload["included_requests"] == 1000
    assert summary_payload["total_remaining_requests"] >= 1000
