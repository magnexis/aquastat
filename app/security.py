from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from enum import Enum

from fastapi import HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings


class AuthTier(str, Enum):
    ANONYMOUS = "anonymous"
    DEVELOPER = "developer"
    ENTERPRISE = "enterprise"


@dataclass
class AccessIdentity:
    tier: AuthTier
    subject: str
    limit: int
    window_seconds: int
    bypass: bool = False


def route_required_scopes(path: str, method: str) -> list[str]:
    normalized = path.lower()
    verb = method.upper()

    if normalized.startswith("/api/v1/control-center/"):
        if normalized.endswith("/overview") or normalized.endswith("/models"):
            return ["usage:read"]
        return ["admin"]
    if normalized.startswith("/api/v1/facilities"):
        if verb == "GET":
            return ["facilities:read"]
        return ["calculations:write"]
    if normalized.startswith("/api/v1/organizations") or normalized.startswith("/api/v1/sources"):
        return ["facilities:read"]
    if normalized.startswith("/api/v1/corrections"):
        return ["facilities:write"]
    if normalized.startswith("/api/v1/ingestion/jobs"):
        return ["admin"]
    if normalized.startswith("/api/v1/estimate") or normalized.startswith("/api/v2/estimate"):
        return ["calculations:read"]
    if normalized.startswith("/api/v1/route-workload") or normalized.startswith("/api/v1/footprint") or normalized.startswith("/api/v2/route-workload") or normalized.startswith("/api/v2/footprint"):
        return ["calculations:write"]
    if normalized.startswith("/api/v1/benchmark") or normalized.startswith("/api/v1/stress-map") or normalized.startswith("/api/v2/benchmark") or normalized.startswith("/api/v2/stress-map"):
        return ["calculations:read"]
    return []


def scopes_allow(request_scopes: list[str], required_scopes: list[str]) -> bool:
    if not required_scopes:
        return True
    if "*" in request_scopes or "admin" in request_scopes:
        return True
    return all(scope in request_scopes for scope in required_scopes)


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)
PUBLIC_PATHS = {
    "/health",
    "/health/live",
    "/health/ready",
    "/metrics",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/version",
    "/control-center",
    "/overview",
    "/calculate",
    "/facilities",
    "/api-keys",
    "/requests",
    "/documentation",
    "/api/v1/status",
    "/api/v1/info",
    "/api/v1/health",
    "/api/v1/regions",
    "/api/v1/control-center/overview",
    "/api/v1/control-center/models",
    "/api/v2/footprint-calculator",
}


def _trusted_proxy_headers() -> list[str]:
    return [item.strip().lower() for item in settings.trusted_proxy_headers.split(",") if item.strip()]


def resolve_client_ip(request: Request) -> str:
    if not settings.trust_proxy:
        return request.client.host if request.client else "unknown"
    for header in _trusted_proxy_headers():
        value = request.headers.get(header)
        if value:
            if header == "x-forwarded-for":
                return value.split(",")[0].strip()
            return value.strip()
    return request.client.host if request.client else "unknown"


def validate_enterprise_signature(request: Request, authorization: str) -> bool:
    if not authorization.startswith("HMAC "):
        return False
    secret = request.headers.get("X-AquaStat-Secret", "")
    timestamp = request.headers.get("X-AquaStat-Timestamp", "")
    if not secret or not timestamp:
        return False
    body_hint = f"{request.method}:{request.url.path}:{timestamp}"
    expected = hmac.new(secret.encode("utf-8"), body_hint.encode("utf-8"), hashlib.sha256).hexdigest()
    supplied = authorization.removeprefix("HMAC ").strip()
    return hmac.compare_digest(expected, supplied)


def hash_api_key(api_key: str) -> str:
    digest = hashlib.sha256(api_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


def mask_api_key(api_key: str) -> str:
    if len(api_key) <= 8:
        return "****"
    return f"{api_key[:6]}***{api_key[-4:]}"


def generate_api_key(prefix: str = "aq_live_") -> tuple[str, str]:
    key = f"{prefix}{secrets.token_urlsafe(24)}"
    return key, hash_api_key(key)


def validate_api_key_format(api_key: str) -> bool:
    return api_key.startswith(("aq_live_", "aq_test_")) and len(api_key) >= 20


def is_public_path(path: str) -> bool:
    return path in PUBLIC_PATHS


def authenticate_api_key(api_key: str | None) -> bool:
    if not api_key or not validate_api_key_format(api_key):
        return False
    hashed = hash_api_key(api_key)
    for candidate in settings.api_key_hashes:
        if hmac.compare_digest(hashed, candidate):
            return True
    return False


def authenticate_admin_api_key(api_key: str | None) -> bool:
    if not api_key or not validate_api_key_format(api_key):
        return False
    hashed = hash_api_key(api_key)
    for candidate in settings.admin_api_key_hashes:
        if hmac.compare_digest(hashed, candidate):
            return True
    return False


def extract_api_key(raw_header: str | None, bearer: HTTPAuthorizationCredentials | None = None, authorization_header: str | None = None) -> str | None:
    if raw_header:
        return raw_header.strip()
    if bearer and bearer.scheme.lower() == "bearer":
        return bearer.credentials.strip()
    if authorization_header and authorization_header.lower().startswith("bearer "):
        return authorization_header[7:].strip()
    return None


async def require_api_key(
    request: Request,
    x_api_key: str | None = None,
    authorization: HTTPAuthorizationCredentials | None = None,
) -> str:
    api_key = extract_api_key(x_api_key, authorization)
    if not authenticate_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
    request.state.authenticated_api_key = mask_api_key(api_key)
    return api_key


async def require_admin_api_key(request: Request) -> str:
    api_key = extract_api_key(
        request.headers.get("X-API-Key"),
        authorization_header=request.headers.get("Authorization"),
    )
    if not authenticate_admin_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is required for this endpoint.",
        )
    request.state.authenticated_api_key = mask_api_key(api_key)
    return api_key


def resolve_access_identity(request: Request, tightened_anonymous: bool = False) -> AccessIdentity:
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer ") and validate_enterprise_signature(request, authorization):
        return AccessIdentity(
            tier=AuthTier.ENTERPRISE,
            subject="enterprise",
            limit=0,
            window_seconds=0,
            bypass=True,
        )

    api_key = extract_api_key(
        request.headers.get("X-API-Key"),
        authorization_header=request.headers.get("Authorization"),
    )
    if api_key and validate_api_key_format(api_key):
        return AccessIdentity(
            tier=AuthTier.DEVELOPER,
            subject=f"api_key:{hash_api_key(api_key)}",
            limit=settings.developer_rate_limit_capacity,
            window_seconds=settings.developer_rate_limit_window_seconds,
        )

    anon_limit = settings.anonymous_rate_limit_capacity
    if tightened_anonymous:
        anon_limit = max(1, int(anon_limit * settings.rate_limit_failure_tightening_factor))
    return AccessIdentity(
        tier=AuthTier.ANONYMOUS,
        subject=f"ip:{resolve_client_ip(request)}",
        limit=anon_limit,
        window_seconds=settings.anonymous_rate_limit_window_seconds,
    )


def rate_limit_headers(limit: int, remaining: int, reset_epoch: int) -> dict[str, str]:
    return {
        "RateLimit-Limit": str(limit),
        "RateLimit-Remaining": str(max(0, remaining)),
        "RateLimit-Reset": str(reset_epoch),
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(max(0, remaining)),
        "X-RateLimit-Reset": str(reset_epoch),
        "Retry-After": str(max(0, reset_epoch - current_epoch())),
    }


def current_epoch() -> int:
    return int(time.time())
