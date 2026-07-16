from __future__ import annotations

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
import yaml

from app.core.config import settings


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
        schema["servers"] = [{"url": settings.public_base_url, "description": "Railway deployment URL placeholder"}]
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
                            },
                            "required": ["code", "message", "requestId"],
                        }
                    },
                    "required": ["error"],
                }
            }
        )
        for path, methods in schema.get("paths", {}).items():
            is_public = path in {"/health", "/metrics", "/api/v1/status", "/api/v1/info", "/api/v1/regions"}
            for method_name, operation in methods.items():
                operation.setdefault("responses", {})
                if not is_public:
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
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi


def render_openapi_yaml(app: FastAPI) -> str:
    return yaml.safe_dump(app.openapi(), sort_keys=False, allow_unicode=True)
