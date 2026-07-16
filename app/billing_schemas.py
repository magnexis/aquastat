from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BillingPackageResponse(BaseModel):
    slug: str
    name: str
    description: str | None = None
    amount_minor: int
    formatted_price: str
    currency: str
    requests_granted: int
    active: bool
    environment: str
    display_order: int
    package_version: str


class BillingPackagesEnvelope(BaseModel):
    items: list[BillingPackageResponse]
    total: int
    billing_status: str


class BillingQuotaGrantSummary(BaseModel):
    grant_id: str
    grant_type: str
    status: str
    requests_granted: int
    requests_consumed: int
    requests_remaining: int
    package_slug: str | None = None
    expires_at: datetime | None = None


class BillingQuotaResponse(BaseModel):
    api_key_id: str
    api_key_prefix: str
    included_requests: int
    remaining_requests: int
    purchased_remaining_requests: int
    total_remaining_requests: int
    grants: list[BillingQuotaGrantSummary]
    billing_status: str


class CreateCheckoutSessionRequest(BaseModel):
    package_slug: str = Field(min_length=1)
    target_api_key_id: str = Field(min_length=1)
    client_request_id: str | None = Field(default=None, min_length=1)


class CheckoutSessionResponse(BaseModel):
    session_id: str
    public_token: str
    status: str
    package_slug: str
    amount_minor: int
    currency: str
    requests_expected: int
    checkout_url: str | None = None
    target_api_key_prefix: str
    expires_at: datetime | None = None
    billing_status: str
    next_action: str
