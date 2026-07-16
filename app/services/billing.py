from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
import secrets
import uuid

from fastapi import HTTPException, status

from app.core.config import settings
from app.services.ops_center import managed_key_store


@dataclass
class BillingPackage:
    slug: str
    name: str
    description: str
    amount_minor: int
    currency: str
    requests_granted: int
    active: bool
    environment: str
    display_order: int
    package_version: str


DEFAULT_PACKAGES = [
    BillingPackage(
        slug="starter-refill",
        name="Starter Refill",
        description="Adds 5,000 requests to the selected API key.",
        amount_minor=500,
        currency="USD",
        requests_granted=5000,
        active=True,
        environment="all",
        display_order=1,
        package_version="1",
    ),
    BillingPackage(
        slug="developer-refill",
        name="Developer Refill",
        description="Adds 25,000 requests to the selected API key.",
        amount_minor=1500,
        currency="USD",
        requests_granted=25000,
        active=True,
        environment="all",
        display_order=2,
        package_version="1",
    ),
    BillingPackage(
        slug="research-refill",
        name="Research Refill",
        description="Adds 100,000 requests to the selected API key.",
        amount_minor=4000,
        currency="USD",
        requests_granted=100000,
        active=True,
        environment="all",
        display_order=3,
        package_version="1",
    ),
]


@dataclass
class CheckoutSession:
    session_id: str
    public_token: str
    status: str
    package_slug: str
    amount_minor: int
    currency: str
    requests_expected: int
    checkout_url: str | None
    target_api_key_id: str
    target_api_key_prefix: str
    expires_at: datetime | None
    billing_status: str
    next_action: str
    created_at: datetime


@dataclass
class QuotaGrant:
    grant_id: str
    api_key_id: str
    api_key_prefix: str
    grant_type: str
    status: str
    requests_granted: int
    requests_consumed: int
    requests_remaining: int
    package_slug: str | None
    expires_at: datetime | None


_checkout_sessions: dict[str, CheckoutSession] = {}
_quota_grants: dict[str, list[QuotaGrant]] = {}


def billing_status() -> str:
    if not settings.billing_enabled:
        return "disabled"
    if not settings.cash_app_pay_enabled:
        return "configured"
    if settings.square_environment == "sandbox":
        return "sandbox"
    return "production"


def list_packages() -> list[dict]:
    items = []
    for package in DEFAULT_PACKAGES:
        if not package.active:
            continue
        items.append(
            {
                **asdict(package),
                "formatted_price": f"${package.amount_minor / 100:.2f}",
            }
        )
    items.sort(key=lambda item: item["display_order"])
    return items


async def get_api_key_record(key_id: str) -> dict | None:
    listing = await managed_key_store.list()
    for item in listing["items"]:
        if item["id"] == key_id:
            return item
    return None


async def quota_summary(key_id: str) -> dict:
    record = await get_api_key_record(key_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    included_requests = int(record.get("usage_limit") or 0)
    grants = _quota_grants.get(key_id, [])
    purchased_remaining = sum(grant.requests_remaining for grant in grants if grant.status == "active")
    included_remaining = included_requests
    total_remaining = included_remaining + purchased_remaining

    return {
        "api_key_id": key_id,
        "api_key_prefix": record["prefix"],
        "included_requests": included_requests,
        "remaining_requests": included_remaining,
        "purchased_remaining_requests": purchased_remaining,
        "total_remaining_requests": total_remaining,
        "grants": [
            {
                "grant_id": grant.grant_id,
                "grant_type": grant.grant_type,
                "status": grant.status,
                "requests_granted": grant.requests_granted,
                "requests_consumed": grant.requests_consumed,
                "requests_remaining": grant.requests_remaining,
                "package_slug": grant.package_slug,
                "expires_at": grant.expires_at,
            }
            for grant in grants
        ],
        "billing_status": billing_status(),
    }


async def create_checkout_session(package_slug: str, target_api_key_id: str, client_request_id: str | None = None) -> dict:
    package = next((item for item in DEFAULT_PACKAGES if item.slug == package_slug and item.active), None)
    if package is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing package not found")

    record = await get_api_key_record(target_api_key_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    now = datetime.now(UTC)
    session_id = f"chk_{uuid.uuid4().hex[:12]}"
    token = secrets.token_urlsafe(24)
    expires_at = now + timedelta(minutes=settings.billing_session_ttl_minutes)
    status_value = "created" if settings.billing_enabled else "unavailable"
    next_action = (
        "Open the hosted Square checkout URL once billing credentials are configured."
        if settings.billing_enabled
        else "Billing is disabled in the current environment."
    )
    checkout_url = None
    if settings.billing_enabled:
        checkout_url = (
            f"{settings.billing_checkout_base_url.rstrip('/')}/billing/checkout/{token}"
        )

    session = CheckoutSession(
        session_id=session_id,
        public_token=token,
        status=status_value,
        package_slug=package.slug,
        amount_minor=package.amount_minor,
        currency=package.currency,
        requests_expected=package.requests_granted,
        checkout_url=checkout_url,
        target_api_key_id=target_api_key_id,
        target_api_key_prefix=record["prefix"],
        expires_at=expires_at,
        billing_status=billing_status(),
        next_action=next_action if client_request_id is None else f"{next_action} Client request id: {client_request_id}",
        created_at=now,
    )
    _checkout_sessions[session_id] = session
    return {
        "session_id": session.session_id,
        "public_token": session.public_token,
        "status": session.status,
        "package_slug": session.package_slug,
        "amount_minor": session.amount_minor,
        "currency": session.currency,
        "requests_expected": session.requests_expected,
        "checkout_url": session.checkout_url,
        "target_api_key_prefix": session.target_api_key_prefix,
        "expires_at": session.expires_at,
        "billing_status": session.billing_status,
        "next_action": session.next_action,
    }


def get_checkout_session(session_id: str) -> dict:
    session = _checkout_sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checkout session not found")
    return {
        "session_id": session.session_id,
        "public_token": session.public_token,
        "status": session.status,
        "package_slug": session.package_slug,
        "amount_minor": session.amount_minor,
        "currency": session.currency,
        "requests_expected": session.requests_expected,
        "checkout_url": session.checkout_url,
        "target_api_key_prefix": session.target_api_key_prefix,
        "expires_at": session.expires_at,
        "billing_status": session.billing_status,
        "next_action": session.next_action,
    }
