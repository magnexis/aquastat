from fastapi import APIRouter, Depends, Query, Request

from app.facility_schemas import (
    BatchEstimateRequest,
    BatchEstimateResponse,
    CorrectionRequest,
    CorrectionResponse,
    ExportRequest,
    ExportResponse,
    FacilityChangesResponse,
    FacilityCompareRequest,
    FacilityCompareResponse,
    FacilityDetailResponse,
    FacilityEstimateResponse,
    FacilityEvidenceResponse,
    FacilityListResponse,
    PublicRecordTemplateResponse,
    FacilitySourcesResponse,
    IngestionJobRequest,
    IngestionJobResponse,
    OrganizationDetailResponse,
    OrganizationListResponse,
    ReviewDecisionResponse,
    ReviewListResponse,
    SourceConnectorListResponse,
    SourceRecordResponse,
)
from app.security import require_admin_api_key
from app.services.facility_intelligence import (
    cancel_ingestion_job,
    compare_facilities,
    create_correction,
    create_ingestion_job,
    decide_review_item,
    estimate_facility,
    estimate_facility_batch,
    export_facilities,
    get_facility_by_slug,
    get_facility_detail,
    get_facility_evidence,
    get_facility_history,
    get_facility_sources,
    get_ingestion_job,
    get_organization,
    get_organization_facilities,
    get_public_record_templates,
    get_review_item,
    get_source,
    list_source_connectors,
    list_facilities,
    list_organizations,
    list_review_items,
)


router = APIRouter()


@router.get("/facilities", response_model=FacilityListResponse, tags=["facilities"])
async def get_facilities(
    query: str | None = Query(default=None),
    operator: str | None = Query(default=None),
    country: str | None = Query(default=None),
    state: str | None = Query(default=None),
    facility_type: str | None = Query(default=None),
    operational_status: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
) -> FacilityListResponse:
    payload = list_facilities(
        {
            "query": query,
            "operator": operator,
            "country": country,
            "state": state,
            "facility_type": facility_type,
            "operational_status": operational_status,
        },
        cursor=cursor,
        limit=limit,
    )
    return FacilityListResponse.model_validate(payload)


@router.get("/facilities/{facility_id}", response_model=FacilityDetailResponse, tags=["facilities"])
async def get_facility(facility_id: str) -> FacilityDetailResponse:
    return FacilityDetailResponse.model_validate(get_facility_detail(facility_id))


@router.get("/facilities/slug/{slug}", response_model=FacilityDetailResponse, tags=["facilities"])
async def get_facility_by_slug_route(slug: str) -> FacilityDetailResponse:
    facility = get_facility_by_slug(slug)
    if facility is None:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found")
    return FacilityDetailResponse.model_validate(get_facility_detail(facility["id"]))


@router.get("/facilities/{facility_id}/evidence", response_model=FacilityEvidenceResponse, tags=["facilities"])
async def get_facility_evidence_route(facility_id: str) -> FacilityEvidenceResponse:
    return FacilityEvidenceResponse.model_validate(get_facility_evidence(facility_id))


@router.get("/facilities/{facility_id}/sources", response_model=FacilitySourcesResponse, tags=["facilities"])
async def get_facility_sources_route(facility_id: str) -> FacilitySourcesResponse:
    return FacilitySourcesResponse.model_validate(get_facility_sources(facility_id))


@router.get(
    "/facilities/{facility_id}/public-records/templates",
    response_model=PublicRecordTemplateResponse,
    tags=["facilities"],
)
async def get_public_record_templates_route(facility_id: str) -> PublicRecordTemplateResponse:
    return PublicRecordTemplateResponse.model_validate(get_public_record_templates(facility_id))


@router.get("/facilities/{facility_id}/history", response_model=FacilityChangesResponse, tags=["facilities"])
async def get_facility_history_route(facility_id: str) -> FacilityChangesResponse:
    return FacilityChangesResponse.model_validate(get_facility_history(facility_id))


@router.get("/facilities/{facility_id}/changes", response_model=FacilityChangesResponse, tags=["facilities"])
async def get_facility_changes_route(facility_id: str) -> FacilityChangesResponse:
    return FacilityChangesResponse.model_validate(get_facility_history(facility_id))


@router.post("/facilities/{facility_id}/estimate", response_model=FacilityEstimateResponse, tags=["facilities"])
async def estimate_facility_route(facility_id: str) -> FacilityEstimateResponse:
    return FacilityEstimateResponse.model_validate(await estimate_facility(facility_id))


@router.post("/facilities/estimate-batch", response_model=BatchEstimateResponse, tags=["facilities"])
async def estimate_facility_batch_route(payload: BatchEstimateRequest) -> BatchEstimateResponse:
    return BatchEstimateResponse.model_validate(await estimate_facility_batch(payload.facility_ids))


@router.post("/facilities/compare", response_model=FacilityCompareResponse, tags=["facilities"])
async def compare_facilities_route(payload: FacilityCompareRequest) -> FacilityCompareResponse:
    return FacilityCompareResponse.model_validate(await compare_facilities(payload.facility_ids))


@router.get("/facilities/{facility_id}/export.json", response_model=ExportResponse, tags=["exports"])
async def export_facility_json_route(facility_id: str) -> ExportResponse:
    return ExportResponse.model_validate(await export_facilities([facility_id]))


@router.post("/facilities/export", response_model=ExportResponse, tags=["exports"])
async def export_facilities_route(payload: ExportRequest) -> ExportResponse:
    return ExportResponse.model_validate(await export_facilities(payload.facility_ids))


@router.get("/organizations", response_model=OrganizationListResponse, tags=["organizations"])
async def get_organizations() -> OrganizationListResponse:
    return OrganizationListResponse.model_validate(list_organizations())


@router.get("/organizations/{organization_id}", response_model=OrganizationDetailResponse, tags=["organizations"])
async def get_organization_route(organization_id: str) -> OrganizationDetailResponse:
    return OrganizationDetailResponse.model_validate(get_organization(organization_id))


@router.get("/organizations/{organization_id}/facilities", response_model=FacilityListResponse, tags=["organizations"])
async def get_organization_facilities_route(organization_id: str) -> FacilityListResponse:
    return FacilityListResponse.model_validate(get_organization_facilities(organization_id))


@router.get("/sources/connectors", response_model=SourceConnectorListResponse, tags=["sources"])
async def list_source_connectors_route() -> SourceConnectorListResponse:
    return SourceConnectorListResponse.model_validate(list_source_connectors())


@router.get("/sources/{source_id}", response_model=SourceRecordResponse, tags=["sources"])
async def get_source_route(source_id: str) -> SourceRecordResponse:
    return SourceRecordResponse.model_validate(get_source(source_id))


@router.post("/corrections", response_model=CorrectionResponse, tags=["corrections"])
async def create_correction_route(payload: CorrectionRequest) -> CorrectionResponse:
    return CorrectionResponse.model_validate(create_correction(payload.model_dump()))


@router.post("/ingestion/jobs", response_model=IngestionJobResponse, tags=["ingestion"])
async def create_ingestion_job_route(payload: IngestionJobRequest) -> IngestionJobResponse:
    return IngestionJobResponse.model_validate(create_ingestion_job(payload.model_dump(mode="json")))


@router.get("/ingestion/jobs/{job_id}", response_model=IngestionJobResponse, tags=["ingestion"])
async def get_ingestion_job_route(job_id: str) -> IngestionJobResponse:
    return IngestionJobResponse.model_validate(get_ingestion_job(job_id))


@router.post("/ingestion/jobs/{job_id}/cancel", response_model=IngestionJobResponse, tags=["ingestion"])
async def cancel_ingestion_job_route(job_id: str) -> IngestionJobResponse:
    return IngestionJobResponse.model_validate(cancel_ingestion_job(job_id))


@router.get("/admin/review", response_model=ReviewListResponse, tags=["admin"])
async def get_review_queue(_: str = Depends(require_admin_api_key)) -> ReviewListResponse:
    return ReviewListResponse.model_validate(list_review_items())


@router.get("/admin/review/{candidate_id}", response_model=dict, tags=["admin"])
async def get_review_item_route(candidate_id: str, _: str = Depends(require_admin_api_key)) -> dict:
    return get_review_item(candidate_id)


@router.post("/admin/review/{candidate_id}/approve", response_model=ReviewDecisionResponse, tags=["admin"])
async def approve_review_item(candidate_id: str, _: str = Depends(require_admin_api_key)) -> ReviewDecisionResponse:
    return ReviewDecisionResponse.model_validate(decide_review_item(candidate_id, approved=True))


@router.post("/admin/review/{candidate_id}/reject", response_model=ReviewDecisionResponse, tags=["admin"])
async def reject_review_item(candidate_id: str, _: str = Depends(require_admin_api_key)) -> ReviewDecisionResponse:
    return ReviewDecisionResponse.model_validate(decide_review_item(candidate_id, approved=False))
