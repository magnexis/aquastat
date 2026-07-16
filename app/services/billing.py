from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
import secrets
import uuid

from fastapi import HTTPException, status

from app.core.config import settings
from app.services.ops_center import managed_key_store
from app.services.billing_persistence import (
    append_usage_ledger,
    consume_quota as consume_quota_db,
    get_checkout_session as get_checkout_session_db,
    get_checkout_session_by_square_order_id,
    get_checkout_session_by_token,
    list_billing_packages as list_billing_packages_db,
    list_quota_grants as list_quota_grants_db,
    save_checkout_session,
    save_quota_grant,
    upsert_billing_package,
)
from app.services.square_api import SquareAPIError, create_square_payment_link, square_ready


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
    square_order_id: str | None = None
    square_payment_id: str | None = None


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


async def list_packages() -> list[dict]:
    await _seed_default_packages()
    persisted = await list_billing_packages_db()
    if persisted:
        items = []
        for package in persisted:
            if not package["active"]:
                continue
            items.append(
                {
                    "slug": package["slug"],
                    "name": package["name"],
                    "description": package["description"],
                    "amount_minor": package["amount_minor"],
                    "currency": package["currency"],
                    "requests_granted": package["requests_granted"],
                    "active": package["active"],
                    "environment": package["environment"],
                    "display_order": package["display_order"],
                    "package_version": package["package_version"],
                    "formatted_price": f"${package['amount_minor'] / 100:.2f}",
                }
            )
        items.sort(key=lambda item: item["display_order"])
        return items

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


async def get_checkout_session_lookup(*, session_id: str | None = None, public_token: str | None = None) -> dict | None:
    if session_id:
        persisted = await get_checkout_session_db(session_id)
        if persisted is not None:
            return persisted
        local = _checkout_sessions.get(session_id)
        if local is not None:
            return {
                "session_id": local.session_id,
                "public_token": local.public_token,
                "status": local.status,
                "package_slug": local.package_slug,
                "amount_minor": local.amount_minor,
                "currency": local.currency,
                "requests_expected": local.requests_expected,
                "checkout_url": local.checkout_url,
                "target_api_key_id": local.target_api_key_id,
                "target_api_key_prefix": local.target_api_key_prefix,
                "expires_at": local.expires_at,
                "completed_at": None,
                "square_order_id": local.square_order_id,
                "square_payment_id": local.square_payment_id,
                "billing_status": local.billing_status,
                "next_action": local.next_action,
                "created_at": local.created_at,
            }
    if public_token:
        persisted = await get_checkout_session_by_token(public_token)
        if persisted is not None:
            return persisted
        for local in _checkout_sessions.values():
            if local.public_token == public_token:
                return {
                    "session_id": local.session_id,
                    "public_token": local.public_token,
                    "status": local.status,
                    "package_slug": local.package_slug,
                    "amount_minor": local.amount_minor,
                    "currency": local.currency,
                    "requests_expected": local.requests_expected,
                    "checkout_url": local.checkout_url,
                    "target_api_key_id": local.target_api_key_id,
                    "target_api_key_prefix": local.target_api_key_prefix,
                    "expires_at": local.expires_at,
                    "completed_at": None,
                    "square_order_id": local.square_order_id,
                    "square_payment_id": local.square_payment_id,
                    "billing_status": local.billing_status,
                    "next_action": local.next_action,
                    "created_at": local.created_at,
                }
    return None


async def get_checkout_session_by_order(square_order_id: str) -> dict | None:
    persisted = await get_checkout_session_by_square_order_id(square_order_id)
    if persisted is not None:
        return persisted
    for local in _checkout_sessions.values():
        if local.square_order_id == square_order_id:
            return {
                "session_id": local.session_id,
                "public_token": local.public_token,
                "status": local.status,
                "package_slug": local.package_slug,
                "amount_minor": local.amount_minor,
                "currency": local.currency,
                "requests_expected": local.requests_expected,
                "checkout_url": local.checkout_url,
                "target_api_key_id": local.target_api_key_id,
                "target_api_key_prefix": local.target_api_key_prefix,
                "expires_at": local.expires_at,
                "completed_at": None,
                "square_order_id": local.square_order_id,
                "square_payment_id": local.square_payment_id,
                "billing_status": local.billing_status,
                "next_action": local.next_action,
                "created_at": local.created_at,
            }
    return None


async def quota_summary(key_id: str) -> dict:
    record = await get_api_key_record(key_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    included_requests = int(record.get("usage_limit") or 0)
    grants = await _ensure_included_grant(record)
    included_remaining = sum(
        grant.requests_remaining
        for grant in grants
        if grant.grant_type == "included" and grant.status in {"active", "exhausted"}
    )
    purchased_remaining = sum(
        grant.requests_remaining
        for grant in grants
        if grant.grant_type != "included" and grant.status in {"active", "exhausted"}
    )
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
    package_catalog = await list_packages()
    package_payload = next((item for item in package_catalog if item["slug"] == package_slug and item["active"]), None)
    if package_payload is None:
        package = next((item for item in DEFAULT_PACKAGES if item.slug == package_slug and item.active), None)
    else:
        package = BillingPackage(
            slug=package_payload["slug"],
            name=package_payload["name"],
            description=package_payload["description"],
            amount_minor=package_payload["amount_minor"],
            currency=package_payload["currency"],
            requests_granted=package_payload["requests_granted"],
            active=package_payload["active"],
            environment=package_payload["environment"],
            display_order=package_payload["display_order"],
            package_version=package_payload["package_version"],
        )
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
    square_order_id = None
    square_payment_id = None
    idempotency_key = client_request_id or f"idem_{uuid.uuid4().hex}"
    if settings.billing_enabled and square_ready():
        try:
            square_link = await create_square_payment_link(
                session_id=session_id,
                package_name=package.name,
                package_slug=package.slug,
                amount_minor=package.amount_minor,
                currency=package.currency,
                target_api_key_id=target_api_key_id,
                target_api_key_prefix=record["prefix"],
            )
            checkout_url = square_link["checkout_url"]
            square_order_id = square_link["square_order_id"]
            idempotency_key = square_link["idempotency_key"]
            next_action = "Open the Square-hosted payment link and wait for Square payment.created/payment.updated webhooks to arrive; quota is issued after a settled payment status is observed."
        except SquareAPIError as exc:
            next_action = f"Square checkout creation failed: {exc}"
            checkout_url = f"{settings.billing_checkout_base_url.rstrip('/')}/billing/checkout/{token}"
    elif settings.billing_enabled:
        checkout_url = f"{settings.billing_checkout_base_url.rstrip('/')}/billing/checkout/{token}"

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
        square_order_id=square_order_id,
        square_payment_id=square_payment_id,
    )
    _checkout_sessions[session_id] = session
    await save_checkout_session(
        {
            "id": session.session_id,
            "public_token": session.public_token,
            "target_api_key_id": session.target_api_key_id,
            "target_api_key_prefix": session.target_api_key_prefix,
            "package_slug": session.package_slug,
            "provider": "square",
            "status": session.status,
            "amount_minor": session.amount_minor,
            "currency": session.currency,
            "requests_expected": session.requests_expected,
            "checkout_url": session.checkout_url,
            "idempotency_key": idempotency_key,
            "square_order_id": square_order_id,
            "square_payment_id": square_payment_id,
            "expires_at": session.expires_at,
            "completed_at": None,
            "failed_at": None,
            "canceled_at": None,
            "created_at": session.created_at,
            "updated_at": session.created_at,
        }
    )
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
        "square_order_id": session.square_order_id,
        "square_payment_id": session.square_payment_id,
        "billing_status": session.billing_status,
        "next_action": session.next_action,
    }


async def create_refill_checkout_for_key(
    key_id: str,
    *,
    package_slug: str = "starter-refill",
    client_request_id: str | None = None,
) -> dict | None:
    record = await get_api_key_record(key_id)
    if record is None:
        return None
    if not record.get("project_id"):
        return None
    try:
        checkout = await create_checkout_session(package_slug, key_id, client_request_id)
        if not checkout.get("checkout_url"):
            checkout["checkout_url"] = (
                f"{settings.billing_checkout_base_url.rstrip('/')}/billing/checkout/{checkout['public_token']}"
            )
        return checkout
    except HTTPException:
        return None


async def get_checkout_session(session_id: str) -> dict:
    persisted = await get_checkout_session_db(session_id)
    if persisted is not None:
        persisted["billing_status"] = billing_status()
        return persisted
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
        "square_order_id": session.square_order_id,
        "square_payment_id": session.square_payment_id,
        "billing_status": session.billing_status,
        "next_action": session.next_action,
    }


async def _seed_default_packages() -> None:
    now = datetime.now(UTC)
    for index, package in enumerate(DEFAULT_PACKAGES, start=1):
        await upsert_billing_package(
            {
                "id": f"pkg_{package.slug}",
                "slug": package.slug,
                "name": package.name,
                "description": package.description,
                "amount_minor": package.amount_minor,
                "currency": package.currency,
                "requests_granted": package.requests_granted,
                "active": 1 if package.active else 0,
                "environment": package.environment,
                "display_order": index,
                "package_version": package.package_version,
                "metadata_json": {},
                "created_at": now,
                "updated_at": now,
            }
        )


async def _ensure_included_grant(record: dict) -> list[QuotaGrant]:
    await _seed_default_packages()
    persisted = await list_quota_grants_db(record["id"])
    grants: list[QuotaGrant] = []
    if persisted is not None:
        for item in persisted:
            grants.append(
                QuotaGrant(
                    grant_id=item["grant_id"],
                    api_key_id=item["api_key_id"],
                    api_key_prefix=item["api_key_prefix"],
                    grant_type=item["grant_type"],
                    status=item["status"],
                    requests_granted=item["requests_granted"],
                    requests_consumed=item["requests_consumed"],
                    requests_remaining=item["requests_remaining"],
                    package_slug=item["package_slug"],
                    expires_at=item["expires_at"],
                )
            )
        if any(grant.grant_type == "included" for grant in grants) or record.get("usage_limit") is None:
            _quota_grants[record["id"]] = grants
            return grants

    local_grants = _quota_grants.get(record["id"])
    if local_grants is not None:
        return local_grants

    if record.get("usage_limit") is None:
        return []

    created_at = datetime.now(UTC)
    grant = QuotaGrant(
        grant_id=f"grt_{uuid.uuid4().hex[:12]}",
        api_key_id=record["id"],
        api_key_prefix=record["prefix"],
        grant_type="included",
        status="active",
        requests_granted=int(record["usage_limit"]),
        requests_consumed=0,
        requests_remaining=int(record["usage_limit"]),
        package_slug=None,
        expires_at=None,
    )
    grants.append(grant)
    _quota_grants[record["id"]] = grants
    await save_quota_grant(
        {
            "id": grant.grant_id,
            "api_key_id": grant.api_key_id,
            "api_key_prefix": grant.api_key_prefix,
            "checkout_session_id": None,
            "package_slug": grant.package_slug,
            "grant_type": grant.grant_type,
            "requests_granted": grant.requests_granted,
            "requests_consumed": grant.requests_consumed,
            "requests_remaining": grant.requests_remaining,
            "status": grant.status,
            "starts_at": created_at,
            "expires_at": grant.expires_at,
            "revoked_at": None,
            "revocation_reason": None,
            "created_at": created_at,
            "updated_at": created_at,
        }
    )
    await append_usage_ledger(
        {
            "id": f"led_{uuid.uuid4().hex[:12]}",
            "api_key_id": grant.api_key_id,
            "api_key_prefix": grant.api_key_prefix,
            "quota_grant_id": grant.grant_id,
            "request_id": None,
            "operation": "grant",
            "delta": grant.requests_granted,
            "balance_after": grant.requests_remaining,
            "reason": "included quota seed",
            "metadata_json": {
                "project_id": record.get("project_id"),
                "grant_type": "included",
                "package_slug": None,
            },
            "created_at": created_at,
        }
    )
    return grants


def is_quota_tracked_path(path: str) -> bool:
    if not path.startswith(("/api/v1/", "/api/v2/")):
        return False
    if path.startswith(("/api/v1/billing", "/api/v1/control-center", "/api/v1/status", "/api/v1/info", "/api/v1/regions")):
        return False
    return True


async def consume_quota_for_key(key_id: str, key_prefix: str, request_id: str, path: str) -> dict[str, int | bool]:
    persisted = await consume_quota_db(key_id, request_id, path)
    if persisted is not None:
        return persisted

    grants = _quota_grants.get(key_id, [])
    ordered_grants = sorted(
        grants,
        key=lambda grant: (0 if grant.grant_type == "prepaid" else 1 if grant.grant_type == "included" else 2),
    )
    for grant in ordered_grants:
        if grant.status == "active" and grant.requests_remaining > 0:
            grant.requests_consumed += 1
            grant.requests_remaining -= 1
            if grant.requests_remaining <= 0:
                grant.status = "exhausted"
            return {"allowed": True, "remaining": grant.requests_remaining, "grant_id": grant.grant_id}
    return {"allowed": False, "remaining": 0, "grant_id": None}
