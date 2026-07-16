from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings
from app.security import (
    authenticate_admin_api_key,
    authenticate_api_key,
    extract_api_key,
    is_public_path,
    route_required_scopes,
    scopes_allow,
)
from app.services.ops_center import resolve_managed_api_key


class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if is_public_path(request.url.path) or request.url.path.startswith("/docs") or request.url.path.startswith("/redoc"):
            return await call_next(request)

        request.state.auth_scopes = ["*"]
        request.state.auth_subject = "anonymous"
        api_key = extract_api_key(
            request.headers.get("X-API-Key"),
            authorization_header=request.headers.get("Authorization"),
        )

        if api_key and authenticate_admin_api_key(api_key):
            request.state.auth_scopes = ["admin", "*"]
            request.state.auth_subject = "admin"
        elif api_key and authenticate_api_key(api_key):
            request.state.auth_scopes = ["*"]
            request.state.auth_subject = "operator"
        else:
            managed = await resolve_managed_api_key(api_key)
            if managed is not None:
                request.state.auth_scopes = managed.get("scopes", [])
                request.state.auth_subject = managed.get("id", "managed-key")
                request.state.auth_key_prefix = managed.get("prefix")
            elif settings.api_key_hashes:
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": {
                            "code": "UNAUTHORIZED",
                            "message": "Authentication is required for this endpoint.",
                            "requestId": getattr(request.state, "request_id", "unknown"),
                        }
                    },
                    headers={"WWW-Authenticate": "Bearer"},
                )

        required_scopes = route_required_scopes(request.url.path, request.method)
        if not scopes_allow(getattr(request.state, "auth_scopes", []), required_scopes):
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "FORBIDDEN",
                        "message": "This API key does not have permission to access the endpoint.",
                        "requestId": getattr(request.state, "request_id", "unknown"),
                    }
                },
            )

        return await call_next(request)
