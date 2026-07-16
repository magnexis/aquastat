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
from app.services.billing import consume_quota_for_key, create_refill_checkout_for_key, is_quota_tracked_path


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
                request.state.auth_key_id = managed.get("id")
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

        if getattr(request.state, "auth_key_id", None) and is_quota_tracked_path(request.url.path):
            from app.services.billing import quota_summary

            summary = await quota_summary(request.state.auth_key_id)
            if summary["total_remaining_requests"] <= 0:
                checkout = await create_refill_checkout_for_key(
                    request.state.auth_key_id,
                    client_request_id=getattr(request.state, "request_id", "unknown"),
                )
                return JSONResponse(
                    status_code=402,
                    content={
                        "error": {
                            "code": "QUOTA_EXHAUSTED",
                            "message": "Included and purchased quota for this API key has been exhausted.",
                            "requestId": getattr(request.state, "request_id", "unknown"),
                            "checkoutUrl": checkout.get("checkout_url") if checkout else None,
                            "checkoutSessionId": checkout.get("session_id") if checkout else None,
                            "packageSlug": checkout.get("package_slug") if checkout else None,
                        }
                    },
                )

        response = await call_next(request)

        if (
            getattr(request.state, "auth_key_id", None)
            and is_quota_tracked_path(request.url.path)
            and response.status_code < 400
        ):
            await consume_quota_for_key(
                request.state.auth_key_id,
                getattr(request.state, "auth_key_prefix", "unknown"),
                getattr(request.state, "request_id", f"req_{request.method.lower()}"),
                request.url.path,
            )

        return response
