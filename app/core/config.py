from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AquaStat API"
    app_description: str = "Water-aware infrastructure API for estimating data center water usage and WUE."
    app_version: str = "1.1.0"
    environment: Literal["development", "test", "production"] = "development"
    port: int = 8080
    host: str = "0.0.0.0"
    log_level: Literal["error", "warn", "info", "debug"] = "info"
    api_v1_prefix: str = "/api/v1"
    api_v2_prefix: str = "/api/v2"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/aquastat"
    public_base_url: str = "https://aquastat-api.onrender.com"
    docs_enabled: bool = True
    weather_cache_ttl_seconds: int = 900
    weather_cache_maxsize: int = 256
    state_cache_ttl_seconds: int = 900
    open_meteo_base_url: str = "https://api.open-meteo.com/v1/forecast"
    electricity_maps_base_url: str = "https://api.electricitymap.org/v3"
    electricity_maps_api_key: str | None = None
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = False
    trusted_proxy_headers: str = "cf-connecting-ip,x-forwarded-for"
    trust_proxy: bool = True
    cors_allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://localhost:8000"])
    max_request_body_bytes: int = 5_242_880
    anonymous_rate_limit_capacity: int = 60
    anonymous_rate_limit_window_seconds: int = 3600
    developer_rate_limit_capacity: int = 10000
    developer_rate_limit_window_seconds: int = 86400
    rate_limit_failure_tightening_factor: float = 0.5
    external_circuit_breaker_threshold: int = 5
    external_circuit_breaker_reset_seconds: int = 300
    telemetry_refresh_interval_seconds: int = 300
    ingestion_batch_limit: int = 100
    bootstrap_database_on_startup: bool = False
    request_timeout_seconds: int = 15
    shutdown_timeout_seconds: int = 15
    gallons_per_liter: float = 0.2641720524
    baseline_household_gallons_per_day: float = 300.0
    load_weight_grid: float = 0.5
    load_weight_latency: float = 0.3
    load_weight_carbon: float = 0.2
    api_key_hashes: list[str] = Field(default_factory=list)
    admin_api_key_hashes: list[str] = Field(default_factory=list)
    internal_api_key_plaintext: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_prefix="AQUASTAT_", extra="ignore")

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_allowed_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        return [item.strip() for item in str(value).split(",") if item.strip()]

    @field_validator("api_key_hashes", mode="before")
    @classmethod
    def parse_api_key_hashes(cls, value: str | list[str] | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [item.strip() for item in str(value).split(",") if item.strip()]

    @field_validator("admin_api_key_hashes", mode="before")
    @classmethod
    def parse_admin_api_key_hashes(cls, value: str | list[str] | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [item.strip() for item in str(value).split(",") if item.strip()]


settings = Settings()
