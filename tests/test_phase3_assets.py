from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_metrics_endpoint_renders_prometheus_payload() -> None:
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")


def test_wasm_and_workflow_assets_exist() -> None:
    assert Path("aquastat_edge/Cargo.toml").exists()
    assert Path("aquastat_edge/src/lib.rs").exists()
    assert Path(".github/workflows/deploy.yml").exists()
    assert Path("prometheus.yml").exists()
