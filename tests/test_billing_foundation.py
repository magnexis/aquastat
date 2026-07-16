from fastapi.testclient import TestClient
import json

from app.core.config import settings
from app.main import app
from app.security import generate_api_key
from app.services.billing_webhooks import compute_square_signature


client = TestClient(app)


def test_billing_packages_endpoint_lists_defaults() -> None:
    response = client.get("/api/v1/billing/packages")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 3
    assert payload["items"][0]["slug"] == "starter-refill"


def test_checkout_session_and_quota_summary_for_managed_key() -> None:
    admin_key, admin_hash = generate_api_key("aq_test_")
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
        assert summary.status_code == 403

        summary = client.get(f"/api/v1/billing/quota/{key_record['id']}", headers={"X-API-Key": admin_key})
        assert summary.status_code == 200
        summary_payload = summary.json()
        assert summary_payload["api_key_id"] == key_record["id"]
        assert summary_payload["included_requests"] == 1000
        assert summary_payload["total_remaining_requests"] >= 1000

        checkout_lookup = client.get(
            f"/api/v1/billing/checkout-sessions/{checkout_payload['session_id']}",
            headers={"X-API-Key": admin_key},
        )
        assert checkout_lookup.status_code == 200
        assert checkout_lookup.json()["session_id"] == checkout_payload["session_id"]
    finally:
        settings.admin_api_key_hashes = original_admin


def test_billing_projects_usage_and_csv_export() -> None:
    admin_key, admin_hash = generate_api_key("aq_test_")
    original_admin = settings.admin_api_key_hashes
    settings.admin_api_key_hashes = [admin_hash]
    try:
        project = client.post(
            "/api/v1/billing/projects",
            headers={"X-API-Key": admin_key},
            json={
                "name": "Platform Team",
                "environment": "testing",
                "description": "Project billing test",
                "plan_slug": "developer",
                "owner_email": "platform@example.com",
            },
        )
        assert project.status_code == 200
        project_payload = project.json()

        created = client.post(
            "/api/v1/control-center/api-keys",
            headers={"X-API-Key": admin_key},
            json={
                "name": "project key",
                "description": "project usage test",
                "environment": "testing",
                "scopes": ["calculations:read"],
                "allowed_endpoints": ["/api/v1/estimate"],
                "allowed_origins": [],
                "allowed_ips": [],
                "project_id": project_payload["id"],
                "usage_limit": 5,
            },
        )
        assert created.status_code == 200
        key_record = created.json()["record"]

        grant = client.post(
            f"/api/v1/billing/projects/{project_payload['id']}/grants",
            headers={"X-API-Key": admin_key},
            json={"api_key_id": key_record["id"], "package_slug": "starter-refill", "requests_granted": 20},
        )
        assert grant.status_code == 200
        projects_forbidden = client.get("/api/v1/billing/projects")
        assert projects_forbidden.status_code == 403

        usage = client.get(f"/api/v1/billing/projects/{project_payload['id']}/usage")
        assert usage.status_code == 403

        project_detail = client.get(f"/api/v1/billing/projects/{project_payload['id']}", headers={"X-API-Key": admin_key})
        assert project_detail.status_code == 200
        assert project_detail.json()["id"] == project_payload["id"]

        project_list = client.get("/api/v1/billing/projects", headers={"X-API-Key": admin_key})
        assert project_list.status_code == 200
        assert project_list.json()["total"] >= 1

        usage = client.get(f"/api/v1/billing/projects/{project_payload['id']}/usage", headers={"X-API-Key": admin_key})
        assert usage.status_code == 200
        usage_payload = usage.json()
        assert usage_payload["project"]["id"] == project_payload["id"]
        assert usage_payload["keys_total"] >= 1
        assert usage_payload["usage"]["prepaid_remaining_requests"] >= 20

        csv_export = client.get(f"/api/v1/billing/projects/{project_payload['id']}/usage.csv", headers={"X-API-Key": admin_key})
        assert csv_export.status_code == 200
        assert "project_id,project_name,api_key_id" in csv_export.text
    finally:
        settings.admin_api_key_hashes = original_admin


def test_prepaid_credits_are_consumed_before_included_quota() -> None:
    admin_key, admin_hash = generate_api_key("aq_test_")
    original_admin = settings.admin_api_key_hashes
    settings.admin_api_key_hashes = [admin_hash]
    try:
        project = client.post(
            "/api/v1/billing/projects",
            headers={"X-API-Key": admin_key},
            json={
                "name": "Prepaid First",
                "environment": "testing",
                "description": "prepaid ordering test",
                "plan_slug": "free",
            },
        )
        project_id = project.json()["id"]
        created = client.post(
            "/api/v1/control-center/api-keys",
            headers={"X-API-Key": admin_key},
            json={
                "name": "prepaid ordering key",
                "description": "prepaid ordering test",
                "environment": "testing",
                "scopes": ["calculations:read"],
                "allowed_endpoints": ["/api/v1/estimate"],
                "allowed_origins": [],
                "allowed_ips": [],
                "project_id": project_id,
                "usage_limit": 3,
            },
        )
        managed_key = created.json()["key"]
        key_record = created.json()["record"]
        grant = client.post(
            f"/api/v1/billing/projects/{project_id}/grants",
            headers={"X-API-Key": admin_key},
            json={"api_key_id": key_record["id"], "package_slug": "starter-refill", "requests_granted": 2},
        )
        assert grant.status_code == 200
    finally:
        settings.admin_api_key_hashes = original_admin

    first = client.get(
        "/api/v1/estimate",
        params={"provider": "aws", "region": "us-east-1"},
        headers={"X-API-Key": managed_key},
    )
    second = client.get(
        "/api/v1/estimate",
        params={"provider": "aws", "region": "us-east-1"},
        headers={"X-API-Key": managed_key},
    )
    assert first.status_code == 200
    assert second.status_code == 200

    usage = client.get(f"/api/v1/billing/projects/{project_id}/usage", headers={"X-API-Key": admin_key})
    assert usage.status_code == 200
    usage_payload = usage.json()
    assert usage_payload["usage"]["prepaid_remaining_requests"] == 0
    assert usage_payload["usage"]["included_requests"] >= 3


def test_square_webhook_completes_checkout_and_issues_prepaid_grant() -> None:
    admin_key, admin_hash = generate_api_key("aq_test_")
    original_admin = settings.admin_api_key_hashes
    original_signature = settings.square_webhook_signature_key
    original_notification_url = settings.square_webhook_notification_url
    settings.admin_api_key_hashes = [admin_hash]
    settings.square_webhook_signature_key = "square-test-secret"
    settings.square_webhook_notification_url = "http://testserver/api/v1/billing/webhooks/square"
    try:
        project = client.post(
            "/api/v1/billing/projects",
            headers={"X-API-Key": admin_key},
            json={
                "name": "Webhook Project",
                "environment": "testing",
                "description": "webhook payment completion test",
                "plan_slug": "developer",
            },
        )
        project_id = project.json()["id"]
        created = client.post(
            "/api/v1/control-center/api-keys",
            headers={"X-API-Key": admin_key},
            json={
                "name": "webhook key",
                "description": "webhook payment completion test",
                "environment": "testing",
                "scopes": ["calculations:read"],
                "allowed_endpoints": ["/api/v1/estimate"],
                "allowed_origins": [],
                "allowed_ips": [],
                "project_id": project_id,
                "usage_limit": 1,
            },
        )
        key_record = created.json()["record"]
        checkout = client.post(
            "/api/v1/billing/checkout-sessions",
            json={
                "package_slug": "starter-refill",
                "target_api_key_id": key_record["id"],
                "client_request_id": "webhook-test-1",
            },
        )
        checkout_payload = checkout.json()
        webhook_payload = {
            "provider_event_id": "evt_test_123",
            "session_id": checkout_payload["session_id"],
            "payment_status": "completed",
            "amount_minor": checkout_payload["amount_minor"],
            "currency": checkout_payload["currency"],
            "paid_at": "2026-07-16T15:00:00Z",
            "metadata": {"square_payment_id": "pay_123"},
        }
        raw = json.dumps(webhook_payload).encode("utf-8")
        signature = compute_square_signature(raw)
        webhook = client.post(
            "/api/v1/billing/webhooks/square",
            content=raw,
            headers={"x-square-hmacsha256-signature": signature, "Content-Type": "application/json"},
        )
        assert webhook.status_code == 200
        assert webhook.json()["grant_issued"] is True
        usage = client.get(f"/api/v1/billing/projects/{project_id}/usage", headers={"X-API-Key": admin_key})
        assert usage.status_code == 200
        assert usage.json()["usage"]["prepaid_remaining_requests"] >= 5000
    finally:
        settings.admin_api_key_hashes = original_admin
        settings.square_webhook_signature_key = original_signature
        settings.square_webhook_notification_url = original_notification_url


def test_square_payment_created_webhook_is_accepted_without_grant() -> None:
    original_signature = settings.square_webhook_signature_key
    original_notification_url = settings.square_webhook_notification_url
    settings.square_webhook_signature_key = "square-test-secret"
    settings.square_webhook_notification_url = "http://testserver/api/v1/billing/webhooks/square"
    try:
        webhook_payload = {
            "type": "payment.created",
            "event_id": "evt_created_123",
            "created_at": "2026-07-16T15:00:00Z",
            "data": {
                "object": {
                    "payment": {
                        "id": "pay_created_123",
                        "order_id": "order_created_123",
                        "status": "PENDING",
                        "amount_money": {"amount": 500, "currency": "USD"},
                        "updated_at": "2026-07-16T15:00:00Z",
                    }
                }
            },
        }
        raw = json.dumps(webhook_payload).encode("utf-8")
        signature = compute_square_signature(raw)
        webhook = client.post(
            "/api/v1/billing/webhooks/square",
            content=raw,
            headers={"x-square-hmacsha256-signature": signature, "Content-Type": "application/json"},
        )
    finally:
        settings.square_webhook_signature_key = original_signature
        settings.square_webhook_notification_url = original_notification_url

    assert webhook.status_code == 202


def test_quota_exhaustion_returns_402_for_managed_key() -> None:
    admin_key, admin_hash = generate_api_key("aq_test_")
    original_admin = settings.admin_api_key_hashes
    settings.admin_api_key_hashes = [admin_hash]
    try:
        created = client.post(
            "/api/v1/control-center/api-keys",
            headers={"X-API-Key": admin_key},
            json={
                "name": "tiny quota key",
                "description": "quota exhaustion test",
                "environment": "testing",
                "scopes": ["calculations:read"],
                "allowed_endpoints": ["/api/v1/estimate"],
                "allowed_origins": [],
                "allowed_ips": [],
                "usage_limit": 1,
            },
        )
    finally:
        settings.admin_api_key_hashes = original_admin

    managed_key = created.json()["key"]
    first = client.get(
        "/api/v1/estimate",
        params={"provider": "aws", "region": "us-east-1"},
        headers={"X-API-Key": managed_key},
    )
    assert first.status_code == 200

    second = client.get(
        "/api/v1/estimate",
        params={"provider": "aws", "region": "us-east-1"},
        headers={"X-API-Key": managed_key},
    )
    assert second.status_code == 402
    assert second.json()["error"]["code"] == "QUOTA_EXHAUSTED"
    assert second.json()["error"]["checkoutUrl"] is None


def test_quota_exhaustion_returns_checkout_for_project_key() -> None:
    admin_key, admin_hash = generate_api_key("aq_test_")
    original_admin = settings.admin_api_key_hashes
    settings.admin_api_key_hashes = [admin_hash]
    try:
        project = client.post(
            "/api/v1/billing/projects",
            headers={"X-API-Key": admin_key},
            json={
                "name": "Checkout Project",
                "environment": "testing",
                "description": "quota checkout test",
                "plan_slug": "developer",
            },
        )
        project_id = project.json()["id"]
        created = client.post(
            "/api/v1/control-center/api-keys",
            headers={"X-API-Key": admin_key},
            json={
                "name": "quota checkout key",
                "description": "quota checkout test",
                "environment": "testing",
                "scopes": ["calculations:read"],
                "allowed_endpoints": ["/api/v1/estimate"],
                "allowed_origins": [],
                "allowed_ips": [],
                "project_id": project_id,
                "usage_limit": 1,
            },
        )
    finally:
        settings.admin_api_key_hashes = original_admin

    managed_key = created.json()["key"]
    first = client.get(
        "/api/v1/estimate",
        params={"provider": "aws", "region": "us-east-1"},
        headers={"X-API-Key": managed_key},
    )
    assert first.status_code == 200

    second = client.get(
        "/api/v1/estimate",
        params={"provider": "aws", "region": "us-east-1"},
        headers={"X-API-Key": managed_key},
    )
    assert second.status_code == 402
    payload = second.json()["error"]
    assert payload["code"] == "QUOTA_EXHAUSTED"
    assert payload["checkoutUrl"]
    assert payload["checkoutSessionId"]
