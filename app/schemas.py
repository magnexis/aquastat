from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models import CoolingType


class DataCenterSummary(BaseModel):
    id: UUID
    name: str
    provider: str
    region_slug: str
    latitude: float
    longitude: float
    max_it_capacity_mw: float
    pue: float
    cooling_type: CoolingType
    base_wue: float
    grid_zone_id: str | None = None
    water_stress_score: float | None = None
    ping_target_ip: str | None = None


class EstimateQuery(BaseModel):
    provider: str = Field(min_length=1)
    region: str = Field(min_length=1)
    load_mw: float | None = Field(default=None, gt=0)


class EstimateDataCenter(BaseModel):
    id: UUID
    provider: str
    region_slug: str
    cooling_type: CoolingType


class WeatherSnapshot(BaseModel):
    dry_bulb_temp_c: float
    relative_humidity_pct: float
    calculated_wet_bulb_temp_c: float
    source: str | None = None
    quality: str | None = None


class WaterMetrics(BaseModel):
    estimated_it_load_mw: float
    calculated_instant_wue: float
    water_consumption_liters_per_hour: float
    water_consumption_gallons_per_hour: float
    equivalent_household_daily_water_usage: float


class EstimateResponse(BaseModel):
    datacenter: EstimateDataCenter
    timestamp: datetime
    weather_snapshot: WeatherSnapshot
    water_metrics: WaterMetrics


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: datetime


class StatusResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    documentation: str
    openapi: str


class APIInfoResponse(BaseModel):
    name: str
    description: str
    version: str
    documentation: str
    openapi: str
    health: str


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    requestId: str
    details: list[ErrorDetail] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class RouteWorkloadRequest(BaseModel):
    job_duration_hours: float = Field(gt=0)
    compute_demand_mwh: float = Field(gt=0)
    candidate_regions: list[str] = Field(min_length=1)


class RoutingMatrixEntry(BaseModel):
    region: str
    projected_water_liters: float
    projected_carbon_g: float
    water_stress_adjusted_impact_score: float


class RouteWorkloadResponse(BaseModel):
    optimal_region: str
    explanation: str
    routing_matrix: list[RoutingMatrixEntry]


class StressMapProperties(BaseModel):
    provider: str
    region_slug: str
    weighted_impact_score: float
    true_green_index: float
    water_stress_score: float
    water_stress_tier: str
    current_carbon_intensity_g_per_kwh: float
    estimated_it_load_mw: float


class GeoJsonFeature(BaseModel):
    type: str = "Feature"
    geometry: dict
    properties: StressMapProperties


class StressMapResponse(BaseModel):
    type: str = "FeatureCollection"
    features: list[GeoJsonFeature]


class BenchmarkEntry(BaseModel):
    region: str
    provider: str
    pue: float
    instant_wue: float
    stress_adjusted_wue: float
    true_green_index: float
    carbon_intensity_g_per_kwh: float
    weighted_impact_score: float
    water_stress_tier: str


class BenchmarkResponse(BaseModel):
    generated_at: datetime
    rankings: list[BenchmarkEntry]


class FootprintSummary(BaseModel):
    provider_detected: str
    estimated_compute_mwh: float
    estimated_water_liters: float
    estimated_water_gallons: float
    olympic_pools: float
    recommended_region: str
    true_green_index: float


class FootprintBreakdownEntry(BaseModel):
    line_item: str
    region: str
    estimated_mwh: float
    estimated_water_liters: float


class AIEstimateRequest(BaseModel):
    model_class: str = Field(min_length=1)
    token_count: int = Field(gt=0)
    response_type: str = Field(min_length=1)
    estimated_watt_hours: float = Field(gt=0)
    region: str = Field(min_length=1)


class AIEstimateResponse(BaseModel):
    direct_water_liters: float
    indirect_water_liters: float
    uncertainty: float


class FootprintResponse(BaseModel):
    summary: FootprintSummary
    breakdown: list[FootprintBreakdownEntry]
