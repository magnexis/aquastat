from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.security import rate_limit_headers, resolve_access_identity
from app.services.circuit_breaker import circuit_breaker
from app.services.state_store import state_store


class TieredRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in {"/health", "/metrics", "/docs", "/openapi.json", "/redoc"} or request.url.path.startswith("/docs"):
            return await call_next(request)

        tightened = circuit_breaker.is_open("open-meteo") or circuit_breaker.is_open("electricity-maps")
        identity = resolve_access_identity(request, tightened_anonymous=tightened)
        if identity.bypass:
            response = await call_next(request)
            response.headers.update(rate_limit_headers(0, 0, 0))
            return response

        decision = await state_store.evaluate_rate_limit(identity.subject, identity.limit, identity.window_seconds)
        if not decision.allowed:
            response = JSONResponse(
                {
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "The request limit has been exceeded.",
                        "requestId": getattr(request.state, "request_id", "unknown"),
                    }
                },
                status_code=429,
            )
            response.headers.update(rate_limit_headers(decision.limit, decision.remaining, decision.reset_epoch))
            return response

        response = await call_next(request)
        response.headers.update(rate_limit_headers(decision.limit, decision.remaining, decision.reset_epoch))
        return response
