from __future__ import annotations

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
import yaml

from app.core.config import settings
from app.security import PUBLIC_PATHS


def _stable_operation_id(method: str, path: str) -> str:
    normalized = path.strip("/").replace("{", "").replace("}", "")
    parts = [segment.replace("-", "_") for segment in normalized.split("/") if segment]
    slug = "_".join(parts) if parts else "root"
    return f"{method.lower()}_{slug}"


def _is_public_operation(path: str) -> bool:
    if path in PUBLIC_PATHS:
        return True
    return path.startswith("/docs") or path.startswith("/redoc")


def install_openapi(app: FastAPI) -> None:
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=settings.app_name,
            version=settings.app_version,
            description=settings.app_description,
            routes=app.routes,
        )
        schema["openapi"] = "3.1.0"
        schema["servers"] = [
            {"url": "http://localhost:8080", "description": "Local development"},
            {"url": settings.public_base_url, "description": "Configured public deployment"},
        ]
        schema.setdefault("components", {}).setdefault("securitySchemes", {}).update(
            {
                "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"},
                "BearerAuth": {"type": "http", "scheme": "bearer"},
            }
        )
        schema["components"].setdefault("schemas", {}).update(
            {
                "ErrorResponse": {
                    "type": "object",
                    "properties": {
                        "error": {
                            "type": "object",
                            "properties": {
                                "code": {"type": "string"},
                                "message": {"type": "string"},
                                "requestId": {"type": "string"},
                                "details": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "field": {"type": "string"},
                                            "message": {"type": "string"},
                                        },
                                        "required": ["field", "message"],
                                    },
                                },
                            },
                            "required": ["code", "message", "requestId"],
                            "example": {
                                "code": "VALIDATION_ERROR",
                                "message": "The request contains invalid data.",
                                "requestId": "req_1234567890",
                                "details": [{"field": "provider", "message": "Field required"}],
                            },
                        }
                    },
                    "required": ["error"],
                }
            }
        )
        for path, methods in schema.get("paths", {}).items():
            for method_name, operation in methods.items():
                operation["operationId"] = _stable_operation_id(method_name, path)
                operation.setdefault("responses", {})
                if not _is_public_operation(path):
                    operation["security"] = [{"ApiKeyAuth": []}, {"BearerAuth": []}]
                operation["responses"].setdefault(
                    "401",
                    {
                        "description": "Unauthorized",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        },
                    },
                )
                operation["responses"].setdefault(
                    "403",
                    {
                        "description": "Forbidden",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        },
                    },
                )
                operation["responses"].setdefault(
                    "404",
                    {
                        "description": "Not found",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        },
                    },
                )
                operation["responses"].setdefault(
                    "429",
                    {
                        "description": "Rate limit exceeded",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        },
                    },
                )
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi


def render_openapi_yaml(app: FastAPI) -> str:
    return yaml.safe_dump(app.openapi(), sort_keys=False, allow_unicode=True)
