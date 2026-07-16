from __future__ import annotations

import logging
import re
import time
import uuid
from datetime import UTC, datetime

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.security import resolve_client_ip
from app.services.ops_center import record_request_activity


logger = logging.getLogger("aquastat.requests")
SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("X-Request-ID")
        request_id = incoming if incoming and SAFE_REQUEST_ID.match(incoming) else str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()

        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000.0, 2)
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": resolve_client_ip(request),
            },
        )
        await record_request_activity(
            {
                "id": f"req_{uuid.uuid4().hex[:12]}",
                "request_id": request_id,
                "timestamp": datetime.now(UTC),
                "created_at": datetime.now(UTC),
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": resolve_client_ip(request),
                "api_key_prefix": (request.headers.get("X-API-Key") or "")[:12] or None,
                "rate_limit_class": response.headers.get("X-RateLimit-Limit", "n/a"),
                "provider": request.query_params.get("provider"),
                "region": request.query_params.get("region"),
            }
        )
        return response
