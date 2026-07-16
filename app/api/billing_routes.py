from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import PlainTextResponse

from app.billing_schemas import (
    BillingWebhookRequest,
    BillingWebhookResponse,
    BillingProjectsEnvelope,
    BillingProjectResponse,
    BillingProjectUsageResponse,
    BillingPackagesEnvelope,
    BillingQuotaResponse,
    CheckoutSessionResponse,
    CreateBillingProjectRequest,
    CreateCheckoutSessionRequest,
    GrantProjectCreditsRequest,
    GrantProjectCreditsResponse,
)
from app.core.config import settings
from app.security import require_admin_api_key
from app.services.billing import create_checkout_session, get_checkout_session, list_packages, quota_summary, billing_status
from app.services.billing_projects import (
    DEFAULT_PROJECT_PLANS,
    create_project,
    export_project_usage_csv,
    get_project,
    grant_prepaid_refill,
    list_projects,
    project_usage_summary,
)
from app.services.billing_webhooks import complete_checkout_from_webhook, parse_webhook_body, verify_square_webhook_signature


router = APIRouter()


@router.get("/billing/packages", response_model=BillingPackagesEnvelope, tags=["billing"])
async def get_billing_packages() -> BillingPackagesEnvelope:
    items = await list_packages()
    return BillingPackagesEnvelope(items=items, total=len(items), billing_status=billing_status())


@router.get("/billing/projects", response_model=BillingProjectsEnvelope, tags=["billing"])
async def get_billing_projects() -> BillingProjectsEnvelope:
    items = [BillingProjectResponse.model_validate(item | {"subscription": item.get("subscription")}) for item in [await get_project(row["id"]) for row in await list_projects()]]
    plans = [
        {
            "slug": plan.slug,
            "name": plan.name,
            "monthly_price_minor": plan.monthly_price_minor,
            "included_requests": plan.included_requests,
        }
        for plan in DEFAULT_PROJECT_PLANS
    ]
    return BillingProjectsEnvelope(items=items, total=len(items), plans=plans)


@router.post("/billing/projects", response_model=BillingProjectResponse, tags=["billing"])
async def post_billing_project(
    payload: CreateBillingProjectRequest,
    _: str = Depends(require_admin_api_key),
) -> BillingProjectResponse:
    created = await create_project(**payload.model_dump())
    return BillingProjectResponse.model_validate(created)


@router.get("/billing/projects/{project_id}", response_model=BillingProjectResponse, tags=["billing"])
async def get_billing_project(project_id: str) -> BillingProjectResponse:
    return BillingProjectResponse.model_validate(await get_project(project_id))


@router.get("/billing/projects/{project_id}/usage", response_model=BillingProjectUsageResponse, tags=["billing"])
async def get_billing_project_usage(project_id: str) -> BillingProjectUsageResponse:
    return BillingProjectUsageResponse.model_validate(await project_usage_summary(project_id))


@router.get("/billing/projects/{project_id}/usage.csv", response_class=PlainTextResponse, tags=["billing"])
async def get_billing_project_usage_csv(project_id: str) -> PlainTextResponse:
    return PlainTextResponse(
        content=await export_project_usage_csv(project_id),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="aquastat-project-{project_id}-usage.csv"'},
    )


@router.post("/billing/projects/{project_id}/grants", response_model=GrantProjectCreditsResponse, tags=["billing"])
async def post_billing_project_grant(
    project_id: str,
    payload: GrantProjectCreditsRequest,
    _: str = Depends(require_admin_api_key),
) -> GrantProjectCreditsResponse:
    return GrantProjectCreditsResponse.model_validate(
        await grant_prepaid_refill(project_id, payload.api_key_id, payload.package_slug, payload.requests_granted)
    )


@router.post("/billing/webhooks/square", response_model=BillingWebhookResponse, tags=["billing"])
async def post_square_webhook(
    request: Request,
    x_square_signature: str | None = Header(default=None, alias="x-square-hmacsha256-signature"),
) -> BillingWebhookResponse:
    raw_body = await request.body()
    notification_url = settings.square_webhook_notification_url or str(request.url)
    if not verify_square_webhook_signature(raw_body, x_square_signature, notification_url=notification_url):
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Square webhook signature")
    payload = BillingWebhookRequest.model_validate(parse_webhook_body(raw_body))
    return BillingWebhookResponse.model_validate(await complete_checkout_from_webhook(payload.model_dump()))


@router.get("/billing/quota/{api_key_id}", response_model=BillingQuotaResponse, tags=["billing"])
async def get_billing_quota(api_key_id: str) -> BillingQuotaResponse:
    return BillingQuotaResponse.model_validate(await quota_summary(api_key_id))


@router.post("/billing/checkout-sessions", response_model=CheckoutSessionResponse, tags=["billing"])
async def post_checkout_session(payload: CreateCheckoutSessionRequest) -> CheckoutSessionResponse:
    return CheckoutSessionResponse.model_validate(
        await create_checkout_session(payload.package_slug, payload.target_api_key_id, payload.client_request_id)
    )


@router.get("/billing/checkout-sessions/{session_id}", response_model=CheckoutSessionResponse, tags=["billing"])
async def get_checkout_session_route(session_id: str) -> CheckoutSessionResponse:
    return CheckoutSessionResponse.model_validate(await get_checkout_session(session_id))
