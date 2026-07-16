from __future__ import annotations

from datetime import UTC, datetime
import uuid

import httpx

from app.core.config import settings


class SquareConfigurationError(RuntimeError):
    pass


class SquareAPIError(RuntimeError):
    pass


def square_base_url() -> str:
    if settings.square_environment == "sandbox":
        return "https://connect.squareupsandbox.com"
    return "https://connect.squareup.com"


def square_ready() -> bool:
    return bool(settings.square_access_token and settings.square_location_id)


def require_square_ready() -> None:
    if not square_ready():
        raise SquareConfigurationError("Square credentials are not fully configured.")


async def create_square_payment_link(
    *,
    session_id: str,
    package_name: str,
    package_slug: str,
    amount_minor: int,
    currency: str,
    target_api_key_id: str,
    target_api_key_prefix: str,
) -> dict:
    require_square_ready()
    body = {
        "idempotency_key": f"aquastat-{session_id}-{uuid.uuid4().hex[:8]}",
        "description": f"AquaStat prepaid refill for {package_slug}",
        "quick_pay": {
            "name": package_name,
            "price_money": {"amount": amount_minor, "currency": currency},
            "location_id": settings.square_location_id,
        },
        "checkout_options": {
            "redirect_url": f"{settings.billing_checkout_base_url.rstrip('/')}/control-center#billing",
            "merchant_support_email": "support@aquastat.local",
            "allow_tipping": False,
        },
        "pre_populated_data": {},
    }
    headers = {
        "Authorization": f"Bearer {settings.square_access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Square-Version": settings.square_api_version,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(f"{square_base_url()}/v2/online-checkout/payment-links", json=body, headers=headers)
    if response.status_code >= 400:
        raise SquareAPIError(f"Square create payment link failed with status {response.status_code}: {response.text}")
    payload = response.json()
    payment_link = payload.get("payment_link", {})
    related_resources = payload.get("related_resources", {})
    orders = related_resources.get("orders") or []
    order_id = payment_link.get("order_id") or (orders[0].get("id") if orders else None)
    return {
        "checkout_url": payment_link.get("url"),
        "square_order_id": order_id,
        "square_payment_link_id": payment_link.get("id"),
        "idempotency_key": body["idempotency_key"],
        "created_at": datetime.now(UTC),
        "request_body": body,
        "target_api_key_id": target_api_key_id,
        "target_api_key_prefix": target_api_key_prefix,
    }
