from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_openapi_exposes_json_and_yaml() -> None:
    json_response = client.get("/openapi.json")
    yaml_response = client.get("/openapi.yaml")

    assert json_response.status_code == 200
    assert yaml_response.status_code == 200
    assert json_response.json()["openapi"] == "3.1.0"
    assert "openapi: 3.1.0" in yaml_response.text


def test_openapi_operation_ids_are_unique_and_stable() -> None:
    schema = client.get("/openapi.json").json()
    operation_ids: list[str] = []

    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            operation_id = operation.get("operationId")
            assert operation_id, f"missing operationId for {method.upper()} {path}"
            assert operation_id == f"{method.lower()}_{path.strip('/').replace('{', '').replace('}', '').replace('-', '_').replace('/', '_') or 'root'}"
            operation_ids.append(operation_id)

    assert len(operation_ids) == len(set(operation_ids))


def test_openapi_includes_expected_servers_and_security() -> None:
    schema = client.get("/openapi.json").json()
    servers = {entry["url"] for entry in schema["servers"]}

    assert "http://localhost:8080" in servers
    assert any(url for url in servers if url.startswith("http"))
    assert "ApiKeyAuth" in schema["components"]["securitySchemes"]
    assert "BearerAuth" in schema["components"]["securitySchemes"]

    protected = schema["paths"]["/api/v1/estimate"]["get"]
    public = schema["paths"]["/health"]["get"]

    assert protected["security"] == [{"ApiKeyAuth": []}, {"BearerAuth": []}]
    assert "security" not in public or public["security"] == []
