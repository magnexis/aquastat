from __future__ import annotations

from fastapi import APIRouter

from app.billing_schemas import (
    BillingPackagesEnvelope,
    BillingQuotaResponse,
    CheckoutSessionResponse,
    CreateCheckoutSessionRequest,
)
from app.services.billing import create_checkout_session, get_checkout_session, list_packages, quota_summary, billing_status


router = APIRouter()


@router.get("/billing/packages", response_model=BillingPackagesEnvelope, tags=["billing"])
async def get_billing_packages() -> BillingPackagesEnvelope:
    items = list_packages()
    return BillingPackagesEnvelope(items=items, total=len(items), billing_status=billing_status())


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
    return CheckoutSessionResponse.model_validate(get_checkout_session(session_id))
