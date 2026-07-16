from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class SourceReliability(BaseModel):
    score: int
    tier: str
    explanation: str


class SourceRecordResponse(BaseModel):
    id: str
    title: str
    publisher: str
    source_type: str
    url: HttpUrl
    document_type: str
    publication_date: str
    retrieved_at: str
    license: str | None = None
    jurisdiction: str | None = None
    language: str = "en"
    access_status: str
    parser_version: str
    ingestion_status: str
    review_status: str
    notes: str | None = None
    reliability: SourceReliability


class FieldEvidence(BaseModel):
    field: str
    value: str | float | int | bool | None
    unit: str | None = None
    evidence_class: str
    figure_type: str
    reporting_boundary: str
    source_id: str
    source_type: str
    source_date: str
    extraction_method: str
    verification_status: str
    confidence: float
    value_status: str
    independent_chain_id: str | None = None
    notes: str | None = None


class DataQualitySummary(BaseModel):
    score: int
    label: str
    reasons: list[str]


class FacilityCoverage(BaseModel):
    location: str
    capacity: str
    cooling_system: str
    pue: str
    wue: str
    water_use: str


class SourceSummary(BaseModel):
    total_sources: int
    primary_sources: int
    independent_chains: int
    latest_source_date: str


class WaterSourceComponent(BaseModel):
    type: str
    percent: float | None = None
    status: str


class FacilitySummary(BaseModel):
    id: str
    slug: str
    name: str
    operator: str
    facility_type: str
    operational_status: str
    country: str
    state_or_province: str | None = None
    municipality: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    estimated_it_load_mw: float | None = None
    announced_it_load_mw: float | None = None
    cooling_systems: list[str]
    electricity_grid_region: str | None = None
    verification_status: str
    synthetic: bool
    production_eligible: bool
    data_quality: DataQualitySummary
    coverage: FacilityCoverage
    source_summary: SourceSummary
    warnings: list[str]


class FacilityListResponse(BaseModel):
    items: list[FacilitySummary]
    next_cursor: str | None = None
    total: int


class FacilityDetailResponse(BaseModel):
    facility: FacilitySummary
    aliases: list[str]
    owner: str | None = None
    campus_name: str | None = None
    primary_water_figure: FieldEvidence | None = None
    contradictory_claims: list[FieldEvidence] = Field(default_factory=list)
    water_sources: list[WaterSourceComponent]
    utility_providers: list[str]
    reported_data_year: int | None = None
    confidence_score: int
    record_status: str
    verification_notes: list[str]


class FacilityHistoryEntry(BaseModel):
    changed_at: str
    field: str
    previous_value: str | float | int | None = None
    new_value: str | float | int | None = None
    status: str
    source_id: str | None = None
    summary: str


class FacilityChangesResponse(BaseModel):
    facility_id: str
    changes: list[FacilityHistoryEntry]


class FacilityEvidenceResponse(BaseModel):
    facility_id: str
    evidence: list[FieldEvidence]


class FacilitySourcesResponse(BaseModel):
    facility_id: str
    sources: list[SourceRecordResponse]


class PublicRecordHolder(BaseModel):
    authority: str
    jurisdiction: str
    record_types: list[str]
    rationale: str


class PublicRecordTemplate(BaseModel):
    facility_id: str
    authority: str
    subject: str
    summary: str
    requested_records: list[str]
    body: str
    legal_notes: list[str]


class PublicRecordTemplateResponse(BaseModel):
    facility_id: str
    known_holders: list[PublicRecordHolder]
    templates: list[PublicRecordTemplate]


class SourceConnectorRecord(BaseModel):
    source_id: str
    publisher: str
    source_type: str
    jurisdiction: str | None = None
    access_method: str
    refresh_cadence: str
    parser_version: str
    terms: str
    last_successful_fetch: str | None = None
    last_failure: str | None = None
    checksum_policy: str
    archival_policy: str


class SourceConnectorListResponse(BaseModel):
    items: list[SourceConnectorRecord]
    total: int


class EstimateRange(BaseModel):
    low_liters_per_hour: float
    expected_liters_per_hour: float
    high_liters_per_hour: float


class ProjectionRange(BaseModel):
    daily_liters: float
    monthly_liters: float
    annual_liters: float


class EstimateConfidence(BaseModel):
    score: int
    label: str
    reasons: list[str]


class AssumptionEntry(BaseModel):
    field: str
    value: str | float | int | bool | None
    unit: str | None = None
    status: str
    reason: str
    source_id: str | None = None


class EstimateInputSelection(BaseModel):
    field: str
    selected_value: str | float | int | bool | None
    status: str
    source_id: str | None = None
    alternatives: list[str] = Field(default_factory=list)


class ModelVersions(BaseModel):
    application_version: str
    model_version: str
    facility_profile_version: str
    dataset_versions: dict[str, str]


class FacilityEstimateResponse(BaseModel):
    facility_record: FacilitySummary
    primary_water_figure: FieldEvidence | None = None
    input_selection: list[EstimateInputSelection]
    source_evidence: list[FieldEvidence]
    direct_water: EstimateRange
    indirect_water: EstimateRange
    total_water: EstimateRange
    projections: ProjectionRange
    confidence: EstimateConfidence
    data_quality: DataQualitySummary
    assumptions: list[AssumptionEntry]
    warnings: list[str]
    result_classification: str
    methodology: str
    model_versions: ModelVersions


class BatchEstimateRequest(BaseModel):
    facility_ids: list[str] = Field(min_length=1, max_length=10)


class BatchEstimateItem(BaseModel):
    facility_id: str
    status: str
    estimate: FacilityEstimateResponse | None = None
    error: str | None = None


class BatchEstimateResponse(BaseModel):
    results: list[BatchEstimateItem]
    model_versions: ModelVersions


class FacilityCompareRequest(BaseModel):
    facility_ids: list[str] = Field(min_length=2, max_length=5)


class FacilityComparisonEntry(BaseModel):
    facility_id: str
    facility_name: str
    direct_water_lph: float
    indirect_water_lph: float
    total_water_lph: float
    data_quality_score: int
    estimate_confidence_score: int
    cooling_systems: list[str]
    water_stress_category: str


class FacilityCompareResponse(BaseModel):
    rankings: list[FacilityComparisonEntry]
    explanation: str


class ExportRequest(BaseModel):
    facility_ids: list[str] = Field(min_length=1, max_length=10)
    include_evidence: bool = True


class ExportRecord(BaseModel):
    facility: FacilityDetailResponse
    estimate: FacilityEstimateResponse
    warnings: list[str]
    retrieved_at: datetime


class ExportResponse(BaseModel):
    items: list[ExportRecord]


class OrganizationSummary(BaseModel):
    id: str
    name: str
    legal_name: str | None = None
    organization_type: str
    country: str
    website: HttpUrl | None = None
    facility_ids: list[str]


class OrganizationListResponse(BaseModel):
    items: list[OrganizationSummary]
    total: int


class OrganizationDetailResponse(BaseModel):
    organization: OrganizationSummary
    aliases: list[str]
    relationships: list[dict[str, str]]
    warnings: list[str]


class CorrectionRequest(BaseModel):
    facility_id: str
    field: str
    proposed_value: str
    source_url: HttpUrl
    notes: str | None = Field(default=None, max_length=1000)
    contact_email: str | None = None


class CorrectionResponse(BaseModel):
    correction_id: str
    status: str
    message: str


class CandidateFactResponse(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    field: str
    raw_value: str
    normalized_value: str
    unit: str | None = None
    source_id: str
    extraction_method: str
    confidence: float
    status: str
    review_notes: str | None = None


class ReviewListResponse(BaseModel):
    items: list[CandidateFactResponse]
    total: int


class ReviewDecisionResponse(BaseModel):
    candidate_id: str
    status: str
    message: str


class IngestionJobRequest(BaseModel):
    source_url: HttpUrl
    source_type: str
    dry_run: bool = True
    notes: str | None = Field(default=None, max_length=1000)


class IngestionJobResponse(BaseModel):
    job_id: str
    status: str
    source_url: HttpUrl
    source_type: str
    dry_run: bool
    summary: str
    sources_processed: int
    candidate_facts_created: int
    errors: list[str]
