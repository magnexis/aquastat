from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.security import generate_api_key
from app.services.ops_center import managed_key_store


client = TestClient(app)


def test_control_center_shell_renders() -> None:
    response = client.get("/control-center")
    assert response.status_code == 200
    assert "AquaStat Control Center" in response.text
    assert "Interactive Calculation Workspace" in response.text


def test_version_and_health_variants_work() -> None:
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200
    version = client.get("/version")
    assert version.status_code == 200
    assert version.json()["model_version"] == "2.0.0"


def test_control_center_overview_and_models_work() -> None:
    overview = client.get("/api/v1/control-center/overview")
    assert overview.status_code == 200
    assert overview.json()["metrics"]
    assert overview.json()["request_window"] == "rolling-persistent"

    models = client.get("/api/v1/control-center/models")
    assert models.status_code == 200
    assert models.json()["items"][0]["status"] == "stable"


def test_request_log_and_key_management_require_admin_key() -> None:
    assert client.get("/api/v1/control-center/requests").status_code == 403
    assert client.get("/api/v1/control-center/api-keys").status_code == 403

    original = settings.admin_api_key_hashes
    key, hashed = generate_api_key("aq_test_")
    settings.admin_api_key_hashes = [hashed]
    try:
        create = client.post(
            "/api/v1/control-center/api-keys",
            headers={"X-API-Key": key},
            json={
                "name": "test key",
                "description": "created in tests",
                "environment": "testing",
                "scopes": ["calculations:read"],
                "allowed_endpoints": ["/api/v1/estimate"],
                "allowed_origins": [],
                "allowed_ips": [],
                "usage_limit": 100,
            },
        )
        assert create.status_code == 200
        payload = create.json()
        assert payload["key"].startswith("aq_test_")
        key_id = payload["record"]["id"]

        listing = client.get("/api/v1/control-center/api-keys", headers={"X-API-Key": key})
        assert listing.status_code == 200
        assert listing.json()["total"] >= 1

        revoke = client.post(f"/api/v1/control-center/api-keys/{key_id}/revoke", headers={"X-API-Key": key})
        assert revoke.status_code == 200
        assert revoke.json()["status"] == "revoked"

        audit = client.get("/api/v1/control-center/audit-logs", headers={"X-API-Key": key})
        assert audit.status_code == 200
        assert audit.json()["items"]
    finally:
        settings.admin_api_key_hashes = original


def test_request_activity_is_recorded() -> None:
    client.get("/api/v1/status")
    original = settings.admin_api_key_hashes
    key, hashed = generate_api_key("aq_test_")
    settings.admin_api_key_hashes = [hashed]
    try:
        response = client.get("/api/v1/control-center/requests", headers={"X-API-Key": key})
        assert response.status_code == 200
        assert response.json()["items"]
    finally:
        settings.admin_api_key_hashes = original


def test_managed_key_scopes_are_enforced() -> None:
    original_admin = settings.admin_api_key_hashes
    admin_key, admin_hash = generate_api_key("aq_test_")
    settings.admin_api_key_hashes = [admin_hash]
    try:
        created = client.post(
            "/api/v1/control-center/api-keys",
            headers={"X-API-Key": admin_key},
            json={
                "name": "scoped key",
                "description": "scope test",
                "environment": "testing",
                "scopes": ["facilities:read"],
                "allowed_endpoints": ["/api/v1/facilities"],
                "allowed_origins": [],
                "allowed_ips": [],
                "usage_limit": 50,
            },
        )
        assert created.status_code == 200
        managed_key = created.json()["key"]

        facilities = client.get("/api/v1/facilities", headers={"X-API-Key": managed_key})
        assert facilities.status_code == 200

        estimate = client.get(
            "/api/v1/estimate",
            params={"provider": "aws", "region": "us-east-1"},
            headers={"X-API-Key": managed_key},
        )
        assert estimate.status_code == 403
        assert estimate.json()["error"]["code"] == "FORBIDDEN"
    finally:
        settings.admin_api_key_hashes = original_admin
