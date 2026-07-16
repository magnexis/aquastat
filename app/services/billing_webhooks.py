from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import hmac
import json
import uuid
import base64

from fastapi import HTTPException, status

from app.core.config import settings
from app.services.billing import get_checkout_session_by_order, get_checkout_session_lookup
from app.services.billing_persistence import list_quota_grants, save_checkout_session
from app.services.billing_projects import grant_prepaid_refill
from app.services.ops_center import managed_key_store


def compute_square_signature(body: bytes, notification_url: str | None = None) -> str:
    secret = settings.square_webhook_signature_key or ""
    base = notification_url or settings.square_webhook_notification_url or ""
    digest = hmac.new(secret.encode("utf-8"), (base.encode("utf-8") + body), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def verify_square_webhook_signature(body: bytes, provided_signature: str | None, notification_url: str | None = None) -> bool:
    if not settings.square_webhook_signature_key:
        return False
    if not provided_signature:
        return False
    expected = compute_square_signature(body, notification_url=notification_url)
    return hmac.compare_digest(expected, provided_signature.strip())


async def complete_checkout_from_webhook(payload: dict) -> dict:
    payment_status = str(payload.get("payment_status", "")).lower()
    if payment_status not in {"completed", "paid", "succeeded"}:
        raise HTTPException(status_code=status.HTTP_202_ACCEPTED, detail="Webhook accepted without quota issuance.")

    session = await get_checkout_session_lookup(
        session_id=payload.get("session_id"),
        public_token=payload.get("public_token"),
    )
    if session is None and payload.get("metadata", {}).get("square_order_id"):
        session = await get_checkout_session_by_order(payload["metadata"]["square_order_id"])
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checkout session not found")

    if session.get("completed_at") is not None or session.get("status") == "completed":
        existing_grants = await list_quota_grants(session["target_api_key_id"])
        existing = None
        if existing_grants:
            existing = next(
                (item for item in existing_grants if item.get("checkout_session_id") == session["session_id"]),
                None,
            )
        return {
            "accepted": True,
            "status": "completed",
            "session_id": session["session_id"],
            "grant_issued": existing is not None,
            "grant_id": existing["grant_id"] if existing else None,
            "message": "Checkout session was already completed.",
        }

    listing = await managed_key_store.list()
    key_record = next((item for item in listing["items"] if item["id"] == session["target_api_key_id"]), None)
    if key_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Managed API key for checkout session not found")
    project_id = key_record.get("project_id")
    if not project_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Checkout session target is not attached to a billing project")

    grant_result = await grant_prepaid_refill(
        project_id,
        session["target_api_key_id"],
        session["package_slug"],
        int(session["requests_expected"]),
        checkout_session_id=session["session_id"],
    )
    completed_at = payload.get("paid_at") or datetime.now(UTC)
    if isinstance(completed_at, str):
        completed_at = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
    now = datetime.now(UTC)
    await save_checkout_session(
        {
            "id": session["session_id"],
            "public_token": session["public_token"],
            "target_api_key_id": session["target_api_key_id"],
            "target_api_key_prefix": session["target_api_key_prefix"],
            "package_slug": session["package_slug"],
            "provider": "square",
            "status": "completed",
            "amount_minor": session["amount_minor"],
            "currency": session["currency"],
            "requests_expected": session["requests_expected"],
            "checkout_url": session.get("checkout_url"),
            "idempotency_key": f"wh_{payload.get('provider_event_id', uuid.uuid4().hex)}",
            "square_order_id": payload.get("metadata", {}).get("square_order_id"),
            "square_payment_id": payload.get("metadata", {}).get("square_payment_id") or payload.get("provider_event_id"),
            "expires_at": session.get("expires_at"),
            "completed_at": completed_at,
            "failed_at": None,
            "canceled_at": None,
            "created_at": session.get("created_at", now),
            "updated_at": now,
        }
    )
    return {
        "accepted": True,
        "status": "completed",
        "session_id": session["session_id"],
        "grant_issued": True,
        "grant_id": grant_result["grant_id"],
        "message": "Webhook verified and prepaid quota issued.",
    }


def parse_webhook_body(raw_body: bytes) -> dict:
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook payload") from exc
    if "data" in payload and payload.get("type"):
        payment = (((payload.get("data") or {}).get("object") or {}).get("payment")) or {}
        return {
            "provider_event_id": payload.get("event_id") or payload.get("id") or uuid.uuid4().hex,
            "session_id": None,
            "public_token": None,
            "payment_status": str(payment.get("status", "")).lower(),
            "amount_minor": (((payment.get("amount_money") or {}).get("amount"))),
            "currency": (((payment.get("amount_money") or {}).get("currency"))),
            "paid_at": payment.get("updated_at") or payload.get("created_at"),
            "metadata": {
                "square_order_id": payment.get("order_id"),
                "square_payment_id": payment.get("id"),
                "square_event_type": payload.get("type"),
                "raw_event_id": payload.get("event_id"),
            },
        }
    return payload
