from datetime import datetime

from pydantic import BaseModel, Field


class HealthReadyResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: datetime


class VersionResponse(BaseModel):
    service: str
    application_version: str
    model_version: str
    dataset_versions: dict[str, str]
    generated_at: datetime


class OverviewMetric(BaseModel):
    label: str
    value: float | int | str
    unit: str | None = None
    context: str | None = None


class OverviewChartPoint(BaseModel):
    label: str
    value: float


class ControlCenterOverviewResponse(BaseModel):
    generated_at: datetime
    model_version: str
    request_window: str
    metrics: list[OverviewMetric]
    endpoint_usage: list[OverviewChartPoint]
    facility_usage: list[OverviewChartPoint]
    region_usage: list[OverviewChartPoint]
    cooling_usage: list[OverviewChartPoint]
    confidence_distribution: list[OverviewChartPoint]
    recent_alerts: list[str]
    recent_calculations: list[dict[str, str | int | float]]


class RequestLogEntry(BaseModel):
    request_id: str
    timestamp: datetime
    method: str
    path: str
    status_code: int
    duration_ms: float
    client_ip: str
    api_key_prefix: str | None = None
    rate_limit_class: str
    provider: str | None = None
    region: str | None = None


class RequestLogResponse(BaseModel):
    items: list[RequestLogEntry]
    total: int


class ManagedApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=300)
    environment: str = Field(pattern="^(development|testing|staging|production)$")
    scopes: list[str] = Field(default_factory=list)
    allowed_endpoints: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None
    allowed_origins: list[str] = Field(default_factory=list)
    allowed_ips: list[str] = Field(default_factory=list)
    project_id: str | None = Field(default=None, min_length=1)
    usage_limit: int | None = Field(default=None, ge=1)


class ManagedApiKeyResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    environment: str
    scopes: list[str]
    allowed_endpoints: list[str]
    allowed_origins: list[str]
    allowed_ips: list[str]
    project_id: str | None = None
    usage_limit: int | None = None
    status: str
    prefix: str
    created_at: datetime
    expires_at: datetime | None = None
    last_used_at: datetime | None = None


class ManagedApiKeyCreateResponse(BaseModel):
    key: str
    record: ManagedApiKeyResponse


class ManagedApiKeyListResponse(BaseModel):
    items: list[ManagedApiKeyResponse]
    total: int


class ManagedApiKeyActionResponse(BaseModel):
    id: str
    status: str
    message: str


class AuditEventResponse(BaseModel):
    id: str
    actor: str
    action: str
    target: str
    result: str
    request_id: str | None = None
    client_ip: str | None = None
    metadata_json: dict
    created_at: datetime


class AuditEventListResponse(BaseModel):
    items: list[AuditEventResponse]
    total: int


class ModelRegistryEntry(BaseModel):
    model_id: str
    display_name: str
    semantic_version: str
    status: str
    description: str
    supported_inputs: list[str]
    assumptions: list[str]
    release_date: str
    known_limitations: list[str]


class ModelRegistryResponse(BaseModel):
    items: list[ModelRegistryEntry]
    total: int
