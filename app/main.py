from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.api.meta_routes import get_health, router as meta_router
from app.api.facility_routes import router as facility_router
from app.api.ops_routes import router as ops_router
from app.api.routes import router
from app.api.v1_alias_routes import router as v1_alias_router
from app.api.v2_routes import router as v2_router
from app.core.config import settings
from app.db.bootstrap import bootstrap_database
from app.db.session import engine, get_engine
from app.errors import install_error_handlers
from app.logging_config import configure_logging
from app.middleware.authentication import AuthenticationMiddleware
from app.middleware.rate_limit import TieredRateLimitMiddleware
from app.middleware.request_context import RequestContextMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.metrics import instrument_app
from app.openapi import install_openapi, render_openapi_yaml
from app.services.background import telemetry_refresher
from app.services.state_store import state_store


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.environment == "production" and not settings.api_key_hashes:
        raise RuntimeError("AQUASTAT_API_KEY_HASHES must be configured in production.")
    await bootstrap_database()
    await telemetry_refresher.start()
    yield
    await telemetry_refresher.stop()
    if state_store._redis is not None:
        await state_store._redis.aclose()
    active_engine = engine
    if active_engine is not None:
        await active_engine.dispose()

configure_logging()
app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json",
)
instrument_app(app)
install_error_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Request-ID"],
    expose_headers=["X-Request-ID", "RateLimit-Limit", "RateLimit-Remaining", "RateLimit-Reset", "Retry-After"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(TieredRateLimitMiddleware)
install_openapi(app)
app.include_router(meta_router, prefix=settings.api_v1_prefix)
app.include_router(router, prefix=settings.api_v1_prefix)
app.include_router(facility_router, prefix=settings.api_v1_prefix)
app.include_router(v1_alias_router, prefix=settings.api_v1_prefix)
app.include_router(v2_router, prefix=settings.api_v2_prefix)
app.include_router(ops_router)


app.add_api_route("/health", get_health, methods=["GET"], tags=["meta"])


@app.get("/openapi.yaml", include_in_schema=False)
async def get_openapi_yaml() -> Response:
    return Response(content=render_openapi_yaml(app), media_type="application/yaml")
