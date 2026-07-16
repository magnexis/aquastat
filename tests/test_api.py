from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError as RedisConnectionError

from app.main import app
from app.security import generate_api_key
from app.core.config import settings
from app.services.state_store import state_store


client = TestClient(app)


def test_regions_endpoint_returns_seeded_regions() -> None:
    response = client.get("/api/v1/regions")
    assert response.status_code == 200
    assert "X-RateLimit-Limit" in response.headers
    payload = response.json()
    assert len(payload) >= 5
    assert any(item["region_slug"] == "us-east-1" for item in payload)


def test_estimate_returns_404_for_unknown_region() -> None:
    response = client.get("/api/v1/estimate", params={"provider": "aws", "region": "missing"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_health_status_and_info_endpoints() -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["service"] == "aquastat-api"

    status_response = client.get("/api/v1/status")
    assert status_response.status_code == 200
    assert status_response.json()["documentation"] == "/docs"

    info_response = client.get("/api/v1/info")
    assert info_response.status_code == 200
    assert info_response.json()["openapi"] == "/openapi.json"


def test_docs_and_openapi_are_public() -> None:
    assert client.get("/docs").status_code == 200
    openapi_response = client.get("/openapi.json")
    assert openapi_response.status_code == 200
    assert openapi_response.json()["openapi"] == "3.1.0"
    assert "ApiKeyAuth" in openapi_response.json()["components"]["securitySchemes"]


def test_stress_map_returns_geojson_features() -> None:
    response = client.get("/api/v2/stress-map")
    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) >= 5
    assert payload["features"][0]["geometry"]["type"] == "Point"


def test_v2_estimate_returns_estimate_payload() -> None:
    response = client.get("/api/v2/estimate", params={"provider": "aws", "region": "us-east-1"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["datacenter"]["region_slug"] == "us-east-1"
    assert payload["water_metrics"]["water_consumption_liters_per_hour"] > 0


def test_route_workload_returns_ranked_matrix() -> None:
    response = client.post(
        "/api/v2/route-workload",
        json={
            "job_duration_hours": 4,
            "compute_demand_mwh": 12.5,
            "candidate_regions": ["aws:us-east-1", "aws:eu-west-1", "gcp:asia-southeast1"],
        },
    )
    assert response.status_code == 200
    assert int(response.headers["X-RateLimit-Limit"]) >= 60
    payload = response.json()
    assert payload["optimal_region"] == "aws:eu-west-1"
    assert len(payload["routing_matrix"]) == 3
    assert payload["routing_matrix"][0]["water_stress_adjusted_impact_score"] <= payload["routing_matrix"][1][
        "water_stress_adjusted_impact_score"
    ]


def test_benchmark_returns_true_green_index_rankings() -> None:
    response = client.get("/api/v2/benchmark")
    assert response.status_code == 200
    payload = response.json()
    assert payload["rankings"]
    assert "true_green_index" in payload["rankings"][0]
    assert payload["rankings"][0]["true_green_index"] <= payload["rankings"][-1]["true_green_index"]


def test_footprint_calculator_ui_renders() -> None:
    response = client.get("/api/v2/footprint-calculator")
    assert response.status_code == 200
    assert "Measure Your Water-Score" in response.text


def test_footprint_csv_upload_returns_estimate() -> None:
    csv_body = (
        "ProductName,UsageQuantity,product/region\n"
        "AmazonEC2,120,us-east-1\n"
        "AWSLambda,45000,eu-west-1\n"
    )
    response = client.post(
        "/api/v2/footprint",
        files={"file": ("billing.csv", csv_body, "text/csv")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["estimated_compute_mwh"] > 0
    assert payload["summary"]["estimated_water_liters"] > 0
    assert payload["summary"]["recommended_region"]


def test_developer_api_key_uses_developer_limit_headers() -> None:
    response = client.get("/api/v1/regions", headers={"X-API-Key": "aq_test_example_key_1234567890"})
    assert response.status_code == 200
    assert response.headers["X-RateLimit-Limit"] == "10000"


def test_invalid_api_key_format_falls_back_to_anonymous_limit() -> None:
    response = client.get("/api/v1/regions", headers={"X-API-Key": "dev-key-123"})
    assert response.status_code == 200
    assert response.headers["X-RateLimit-Limit"] == "60"


def test_request_id_header_is_returned() -> None:
    response = client.get("/api/v1/regions", headers={"X-Request-ID": "test-request-1234"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request-1234"


def test_rate_limit_falls_back_when_redis_is_unavailable(monkeypatch) -> None:
    class BrokenRedis:
        async def script_load(self, _: str) -> str:
            raise RedisConnectionError("redis offline")

        async def aclose(self) -> None:
            return None

    async def fake_get_redis():
        return BrokenRedis()

    original_enabled = settings.redis_enabled
    original_redis = state_store._redis
    original_sha = state_store._rl_sha
    monkeypatch.setattr(state_store, "_get_redis", fake_get_redis)
    settings.redis_enabled = True
    state_store._redis = BrokenRedis()
    state_store._rl_sha = None
    try:
        response = client.get("/api/v1/regions")
    finally:
        settings.redis_enabled = original_enabled
        state_store._redis = original_redis
        state_store._rl_sha = original_sha

    assert response.status_code == 200
    assert response.headers["X-RateLimit-Limit"] == "60"


def test_unknown_route_uses_standard_error_shape() -> None:
    response = client.get("/missing-route")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_authentication_required_when_hashes_configured() -> None:
    original = settings.api_key_hashes
    key, hashed = generate_api_key("aq_test_")
    settings.api_key_hashes = [hashed]
    try:
        unauthorized = client.get("/api/v1/estimate", params={"provider": "aws", "region": "us-east-1"})
        assert unauthorized.status_code == 401
        assert unauthorized.json()["error"]["code"] == "UNAUTHORIZED"

        forbidden = client.get(
            "/api/v1/estimate",
            params={"provider": "aws", "region": "us-east-1"},
            headers={"X-API-Key": "aq_test_invalid_key_123456789"},
        )
        assert forbidden.status_code == 401

        allowed = client.get(
            "/api/v1/estimate",
            params={"provider": "aws", "region": "us-east-1"},
            headers={"X-API-Key": key},
        )
        assert allowed.status_code == 200
    finally:
        settings.api_key_hashes = original
