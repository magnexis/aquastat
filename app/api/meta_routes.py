from fastapi import APIRouter

from app.core.config import settings
from app.errors import health_payload
from app.schemas import APIInfoResponse, HealthResponse, StatusResponse


router = APIRouter()


@router.get("/status", response_model=StatusResponse, tags=["meta"])
async def get_status() -> StatusResponse:
    return StatusResponse(
        status="ok",
        service="aquastat-api",
        version=settings.app_version,
        environment=settings.environment,
        documentation="/docs",
        openapi="/openapi.json",
    )


@router.get("/info", response_model=APIInfoResponse, tags=["meta"])
async def get_info() -> APIInfoResponse:
    return APIInfoResponse(
        name=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        documentation="/docs",
        openapi="/openapi.json",
        health="/health",
    )


@router.get("/health", response_model=HealthResponse, tags=["meta"])
async def get_health() -> HealthResponse:
    return HealthResponse.model_validate(health_payload("aquastat-api", settings.app_version))
