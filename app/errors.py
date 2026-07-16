from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


logger = logging.getLogger("aquastat.errors")

ERROR_MESSAGES = {
    "VALIDATION_ERROR": "The request contains invalid data.",
    "UNAUTHORIZED": "Authentication is required for this endpoint.",
    "FORBIDDEN": "You do not have access to this resource.",
    "NOT_FOUND": "The requested resource was not found.",
    "METHOD_NOT_ALLOWED": "The HTTP method is not allowed for this resource.",
    "RATE_LIMIT_EXCEEDED": "The request limit has been exceeded.",
    "CONFLICT": "The request conflicts with the current resource state.",
    "INTERNAL_SERVER_ERROR": "An unexpected internal error occurred.",
    "SERVICE_UNAVAILABLE": "The service is temporarily unavailable.",
}


def error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str | None = None,
    details: list[dict[str, str]] | None = None,
) -> JSONResponse:
    payload: dict[str, object] = {
        "error": {
            "code": code,
            "message": message or ERROR_MESSAGES.get(code, "An error occurred."),
            "requestId": getattr(request.state, "request_id", "unknown"),
        }
    }
    if details:
        payload["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=payload)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = []
        for error in exc.errors():
            location = [str(item) for item in error.get("loc", []) if item != "query" and item != "body" and item != "path"]
            details.append({"field": ".".join(location) or "request", "message": error.get("msg", "Invalid value")})
        return error_response(request, 422, "VALIDATION_ERROR", details=details)

    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        mapping = {
            status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
            status.HTTP_403_FORBIDDEN: "FORBIDDEN",
            status.HTTP_404_NOT_FOUND: "NOT_FOUND",
            status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
            status.HTTP_409_CONFLICT: "CONFLICT",
            status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMIT_EXCEEDED",
            status.HTTP_503_SERVICE_UNAVAILABLE: "SERVICE_UNAVAILABLE",
        }
        code = mapping.get(exc.status_code, "INTERNAL_SERVER_ERROR")
        return error_response(request, exc.status_code, code, message=str(exc.detail))

    @app.exception_handler(StarletteHTTPException)
    async def handle_starlette_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        mapping = {
            status.HTTP_404_NOT_FOUND: "NOT_FOUND",
            status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
        }
        return error_response(request, exc.status_code, mapping.get(exc.status_code, "INTERNAL_SERVER_ERROR"), message=str(exc.detail))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled_exception",
            extra={
                "request_id": getattr(request.state, "request_id", "unknown"),
                "path": str(request.url.path),
                "method": request.method,
                "error_code": "INTERNAL_SERVER_ERROR",
            },
        )
        return error_response(request, 500, "INTERNAL_SERVER_ERROR")


def health_payload(service: str, version: str) -> dict[str, str]:
    return {
        "status": "ok",
        "service": service,
        "version": version,
        "timestamp": datetime.now(UTC).isoformat(),
    }
