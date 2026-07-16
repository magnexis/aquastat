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


class QuotaCheckoutResponse(BaseModel):
    session_id: str
    checkout_url: str | None = None
    package_slug: str


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


class BillingWebhookRequest(BaseModel):
    provider_event_id: str = Field(min_length=1)
    session_id: str | None = None
    public_token: str | None = None
    payment_status: str = Field(min_length=1)
    amount_minor: int | None = None
    currency: str | None = None
    paid_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)


class BillingWebhookResponse(BaseModel):
    accepted: bool
    status: str
    session_id: str
    grant_issued: bool
    grant_id: str | None = None
    message: str


class BillingPlanResponse(BaseModel):
    slug: str
    name: str
    monthly_price_minor: int
    included_requests: int


class BillingSubscriptionResponse(BaseModel):
    id: str
    project_id: str
    plan_slug: str
    plan_name: str
    status: str
    billing_cycle: str
    included_requests: int
    monthly_price_minor: int
    currency: str
    starts_at: datetime
    renews_at: datetime | None = None


class BillingProjectResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None = None
    environment: str
    status: str
    monthly_budget_minor: int | None = None
    soft_budget_minor: int | None = None
    currency: str
    owner_email: str | None = None
    created_at: datetime
    updated_at: datetime
    subscription: BillingSubscriptionResponse | None = None


class BillingProjectsEnvelope(BaseModel):
    items: list[BillingProjectResponse]
    total: int
    plans: list[BillingPlanResponse]


class CreateBillingProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    environment: str = Field(pattern="^(development|testing|staging|production)$")
    description: str | None = Field(default=None, max_length=300)
    plan_slug: str = Field(min_length=1)
    owner_email: str | None = None


class BillingProjectUsageTotals(BaseModel):
    included_requests: int
    prepaid_remaining_requests: int
    consumed_requests: int
    estimated_spend_minor: int
    currency: str
    monthly_budget_minor: int | None = None
    soft_budget_minor: int | None = None
    budget_state: str
    low_credit_threshold_requests: int
    low_credit: bool


class BillingAlertResponse(BaseModel):
    code: str
    severity: str
    message: str
    project_id: str


class BillingProjectUsageResponse(BaseModel):
    project: dict
    subscription: BillingSubscriptionResponse | None = None
    keys_total: int
    keys: list[dict]
    usage: BillingProjectUsageTotals
    alerts: list[BillingAlertResponse]
    usage_activity: list[dict]


class GrantProjectCreditsRequest(BaseModel):
    api_key_id: str = Field(min_length=1)
    package_slug: str = Field(min_length=1)
    requests_granted: int = Field(ge=1)


class GrantProjectCreditsResponse(BaseModel):
    project_id: str
    api_key_id: str
    grant_id: str
    requests_granted: int
