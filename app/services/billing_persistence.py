from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.db.models import (
    BillingCheckoutSession,
    BillingPackage,
    BillingProject,
    BillingSubscription,
    QuotaGrant,
    UsageLedgerEntry,
)
from app.db.session import get_session_factory

_local_projects: dict[str, dict[str, Any]] = {}
_local_subscriptions: dict[str, dict[str, Any]] = {}
_local_usage_ledger: list[dict[str, Any]] = []
_local_quota_grants: dict[str, dict[str, Any]] = {}


async def upsert_billing_package(payload: dict[str, Any]) -> bool:
    try:
        factory = get_session_factory()
        async with factory() as session:
            existing = await session.get(BillingPackage, payload["id"])
            if existing is None:
                existing = BillingPackage(**payload)
                session.add(existing)
            else:
                for key, value in payload.items():
                    setattr(existing, key, value)
            await session.commit()
        return True
    except (SQLAlchemyError, ModuleNotFoundError, OSError, RuntimeError, AttributeError, Exception):
        return False


async def list_billing_packages() -> list[dict[str, Any]] | None:
    try:
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(select(BillingPackage).order_by(BillingPackage.display_order))
            rows = result.scalars().all()
        return [
            {
                "id": row.id,
                "slug": row.slug,
                "name": row.name,
                "description": row.description,
                "amount_minor": row.amount_minor,
                "currency": row.currency,
                "requests_granted": row.requests_granted,
                "active": bool(row.active),
                "environment": row.environment,
                "display_order": row.display_order,
                "package_version": row.package_version,
                "metadata_json": row.metadata_json or {},
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]
    except (SQLAlchemyError, ModuleNotFoundError, OSError, RuntimeError, AttributeError, Exception):
        return None


async def save_checkout_session(payload: dict[str, Any]) -> bool:
    try:
        factory = get_session_factory()
        async with factory() as session:
            existing = await session.get(BillingCheckoutSession, payload["id"])
            if existing is None:
                session.add(BillingCheckoutSession(**payload))
            else:
                for key, value in payload.items():
                    setattr(existing, key, value)
            await session.commit()
        return True
    except (SQLAlchemyError, ModuleNotFoundError, OSError, RuntimeError, AttributeError, Exception):
        return False


async def get_checkout_session(session_id: str) -> dict[str, Any] | None:
    try:
        factory = get_session_factory()
        async with factory() as session:
            row = await session.get(BillingCheckoutSession, session_id)
        if row is None:
            return None
        return {
            "session_id": row.id,
            "public_token": row.public_token,
            "status": row.status,
            "package_slug": row.package_slug,
            "amount_minor": row.amount_minor,
            "currency": row.currency,
            "requests_expected": row.requests_expected,
            "checkout_url": row.checkout_url,
            "target_api_key_id": row.target_api_key_id,
            "target_api_key_prefix": row.target_api_key_prefix,
            "expires_at": row.expires_at,
            "completed_at": row.completed_at,
            "billing_status": "configured",
            "next_action": "Await verified payment completion.",
        }
    except (SQLAlchemyError, ModuleNotFoundError, OSError, RuntimeError, AttributeError, Exception):
        return None


async def get_checkout_session_by_token(public_token: str) -> dict[str, Any] | None:
    try:
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(BillingCheckoutSession).where(BillingCheckoutSession.public_token == public_token)
            )
            row = result.scalar_one_or_none()
        if row is None:
            return None
        return {
            "session_id": row.id,
            "public_token": row.public_token,
            "status": row.status,
            "package_slug": row.package_slug,
            "amount_minor": row.amount_minor,
            "currency": row.currency,
            "requests_expected": row.requests_expected,
            "checkout_url": row.checkout_url,
            "target_api_key_id": row.target_api_key_id,
            "target_api_key_prefix": row.target_api_key_prefix,
            "expires_at": row.expires_at,
            "completed_at": row.completed_at,
            "billing_status": "configured",
            "next_action": "Await verified payment completion.",
        }
    except (SQLAlchemyError, ModuleNotFoundError, OSError, RuntimeError, AttributeError, Exception):
        return None


async def get_checkout_session_by_square_order_id(square_order_id: str) -> dict[str, Any] | None:
    try:
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(BillingCheckoutSession).where(BillingCheckoutSession.square_order_id == square_order_id)
            )
            row = result.scalar_one_or_none()
        if row is None:
            return None
        return {
            "session_id": row.id,
            "public_token": row.public_token,
            "status": row.status,
            "package_slug": row.package_slug,
            "amount_minor": row.amount_minor,
            "currency": row.currency,
            "requests_expected": row.requests_expected,
            "checkout_url": row.checkout_url,
            "target_api_key_id": row.target_api_key_id,
            "target_api_key_prefix": row.target_api_key_prefix,
            "expires_at": row.expires_at,
            "completed_at": row.completed_at,
            "square_order_id": row.square_order_id,
            "square_payment_id": row.square_payment_id,
            "billing_status": "configured",
            "next_action": "Await verified payment completion.",
        }
    except (SQLAlchemyError, ModuleNotFoundError, OSError, RuntimeError, AttributeError, Exception):
        return None


async def save_quota_grant(payload: dict[str, Any]) -> bool:
    _local_quota_grants[payload["id"]] = dict(payload)
    try:
        factory = get_session_factory()
        async with factory() as session:
            existing = await session.get(QuotaGrant, payload["id"])
            if existing is None:
                session.add(QuotaGrant(**payload))
            else:
                for key, value in payload.items():
                    setattr(existing, key, value)
            await session.commit()
        return True
    except (SQLAlchemyError, ModuleNotFoundError, OSError, RuntimeError, AttributeError, Exception):
        return False


async def list_quota_grants(api_key_id: str) -> list[dict[str, Any]] | None:
    try:
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(QuotaGrant)
                .where(QuotaGrant.api_key_id == api_key_id)
                .order_by(QuotaGrant.created_at.asc())
            )
            rows = result.scalars().all()
        return [
            {
                "grant_id": row.id,
                "api_key_id": row.api_key_id,
                "api_key_prefix": row.api_key_prefix,
                "checkout_session_id": row.checkout_session_id,
                "package_slug": row.package_slug,
                "grant_type": row.grant_type,
                "requests_granted": row.requests_granted,
                "requests_consumed": row.requests_consumed,
                "requests_remaining": row.requests_remaining,
                "status": row.status,
                "starts_at": row.starts_at,
                "expires_at": row.expires_at,
                "revoked_at": row.revoked_at,
                "revocation_reason": row.revocation_reason,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]
    except (SQLAlchemyError, ModuleNotFoundError, OSError, RuntimeError, AttributeError, Exception):
        rows = [
            item
            for item in _local_quota_grants.values()
            if item["api_key_id"] == api_key_id
        ]
        rows.sort(key=lambda item: item["created_at"])
        return [
            {
                "grant_id": row["id"],
                "api_key_id": row["api_key_id"],
                "api_key_prefix": row["api_key_prefix"],
                "checkout_session_id": row.get("checkout_session_id"),
                "package_slug": row.get("package_slug"),
                "grant_type": row["grant_type"],
                "requests_granted": row["requests_granted"],
                "requests_consumed": row["requests_consumed"],
                "requests_remaining": row["requests_remaining"],
                "status": row["status"],
                "starts_at": row["starts_at"],
                "expires_at": row.get("expires_at"),
                "revoked_at": row.get("revoked_at"),
                "revocation_reason": row.get("revocation_reason"),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ] or None


async def append_usage_ledger(payload: dict[str, Any]) -> bool:
    _local_usage_ledger.append(dict(payload))
    try:
        factory = get_session_factory()
        async with factory() as session:
            session.add(UsageLedgerEntry(**payload))
            await session.commit()
        return True
    except (SQLAlchemyError, ModuleNotFoundError, OSError, RuntimeError, AttributeError, Exception):
        return False


async def save_project_db(payload: dict[str, Any]) -> bool:
    _local_projects[payload["id"]] = dict(payload)
    try:
        factory = get_session_factory()
        async with factory() as session:
            existing = await session.get(BillingProject, payload["id"])
            if existing is None:
                session.add(BillingProject(**payload))
            else:
                for key, value in payload.items():
                    setattr(existing, key, value)
            await session.commit()
        return True
    except (SQLAlchemyError, ModuleNotFoundError, OSError, RuntimeError, AttributeError, Exception):
        return False


async def list_projects_db() -> list[dict[str, Any]] | None:
    try:
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(select(BillingProject).order_by(BillingProject.created_at.asc()))
            rows = result.scalars().all()
        return [
            {
                "id": row.id,
                "name": row.name,
                "slug": row.slug,
                "description": row.description,
                "environment": row.environment,
                "status": row.status,
                "monthly_budget_minor": row.monthly_budget_minor,
                "soft_budget_minor": row.soft_budget_minor,
                "currency": row.currency,
                "owner_email": row.owner_email,
                "metadata_json": row.metadata_json or {},
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]
    except (SQLAlchemyError, ModuleNotFoundError, OSError, RuntimeError, AttributeError, Exception):
        return list(_local_projects.values()) or None


async def save_subscription_db(payload: dict[str, Any]) -> bool:
    _local_subscriptions[payload["id"]] = dict(payload)
    try:
        factory = get_session_factory()
        async with factory() as session:
            existing = await session.get(BillingSubscription, payload["id"])
            if existing is None:
                session.add(BillingSubscription(**payload))
            else:
                for key, value in payload.items():
                    setattr(existing, key, value)
            await session.commit()
        return True
    except (SQLAlchemyError, ModuleNotFoundError, OSError, RuntimeError, AttributeError, Exception):
        return False


async def list_project_subscriptions_db() -> list[dict[str, Any]] | None:
    try:
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(select(BillingSubscription).order_by(BillingSubscription.created_at.asc()))
            rows = result.scalars().all()
        return [
            {
                "id": row.id,
                "project_id": row.project_id,
                "plan_slug": row.plan_slug,
                "plan_name": row.plan_name,
                "status": row.status,
                "billing_cycle": row.billing_cycle,
                "included_requests": row.included_requests,
                "monthly_price_minor": row.monthly_price_minor,
                "currency": row.currency,
                "starts_at": row.starts_at,
                "renews_at": row.renews_at,
                "canceled_at": row.canceled_at,
                "metadata_json": row.metadata_json or {},
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]
    except (SQLAlchemyError, ModuleNotFoundError, OSError, RuntimeError, AttributeError, Exception):
        return list(_local_subscriptions.values()) or None


async def list_usage_ledger_db(project_id: str | None = None, api_key_id: str | None = None) -> list[dict[str, Any]] | None:
    try:
        factory = get_session_factory()
        async with factory() as session:
            stmt = select(UsageLedgerEntry).order_by(UsageLedgerEntry.created_at.desc())
            if api_key_id is not None:
                stmt = stmt.where(UsageLedgerEntry.api_key_id == api_key_id)
            result = await session.execute(stmt)
            rows = result.scalars().all()
        items: list[dict[str, Any]] = []
        for row in rows:
            metadata_json = row.metadata_json or {}
            if project_id is not None and metadata_json.get("project_id") != project_id:
                continue
            items.append(
                {
                    "id": row.id,
                    "api_key_id": row.api_key_id,
                    "api_key_prefix": row.api_key_prefix,
                    "quota_grant_id": row.quota_grant_id,
                    "request_id": row.request_id,
                    "operation": row.operation,
                    "delta": row.delta,
                    "balance_after": row.balance_after,
                    "reason": row.reason,
                    "metadata_json": metadata_json,
                    "grant_type": metadata_json.get("grant_type"),
                    "created_at": row.created_at,
                }
            )
        return items
    except (SQLAlchemyError, ModuleNotFoundError, OSError, RuntimeError, AttributeError, Exception):
        items = []
        for row in reversed(_local_usage_ledger):
            metadata_json = row.get("metadata_json", {})
            if api_key_id is not None and row["api_key_id"] != api_key_id:
                continue
            if project_id is not None and metadata_json.get("project_id") != project_id:
                continue
            items.append(
                {
                    "id": row["id"],
                    "api_key_id": row["api_key_id"],
                    "api_key_prefix": row["api_key_prefix"],
                    "quota_grant_id": row.get("quota_grant_id"),
                    "request_id": row.get("request_id"),
                    "operation": row["operation"],
                    "delta": row["delta"],
                    "balance_after": row["balance_after"],
                    "reason": row["reason"],
                    "metadata_json": metadata_json,
                    "grant_type": metadata_json.get("grant_type"),
                    "created_at": row["created_at"],
                }
            )
        return items or None


async def consume_quota(api_key_id: str, request_id: str, path: str) -> dict[str, Any] | None:
    try:
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(QuotaGrant)
                .where(
                    QuotaGrant.api_key_id == api_key_id,
                    QuotaGrant.status == "active",
                    QuotaGrant.requests_remaining > 0,
                )
                .order_by(QuotaGrant.grant_type.asc(), QuotaGrant.created_at.asc())
            )
            grants = result.scalars().all()
            grant = next((row for row in grants if row.grant_type == "prepaid"), None)
            if grant is None:
                grant = next((row for row in grants if row.grant_type == "included"), None)
            if grant is None and grants:
                grant = grants[0]
            if grant is None:
                return {"allowed": False, "remaining": 0, "grant_id": None}

            grant.requests_consumed += 1
            grant.requests_remaining -= 1
            if grant.requests_remaining <= 0:
                grant.status = "exhausted"
            grant.updated_at = datetime.now(UTC)

            session.add(
                UsageLedgerEntry(
                    id=f"led_{request_id[-12:]}",
                    api_key_id=grant.api_key_id,
                    api_key_prefix=grant.api_key_prefix,
                    quota_grant_id=grant.id,
                    request_id=request_id,
                    operation="consume",
                    delta=-1,
                    balance_after=grant.requests_remaining,
                    reason=path,
                    metadata_json={"grant_type": grant.grant_type, "package_slug": grant.package_slug},
                    created_at=datetime.now(UTC),
                )
            )
            await session.commit()
            return {"allowed": True, "remaining": grant.requests_remaining, "grant_id": grant.id}
    except (SQLAlchemyError, ModuleNotFoundError, OSError, RuntimeError, AttributeError, Exception):
        grants = [
            item for item in _local_quota_grants.values()
            if item["api_key_id"] == api_key_id and item["status"] == "active" and item["requests_remaining"] > 0
        ]
        grants.sort(key=lambda item: item["created_at"])
        grant = next((row for row in grants if row["grant_type"] == "prepaid"), None)
        if grant is None:
            grant = next((row for row in grants if row["grant_type"] == "included"), None)
        if grant is None and grants:
            grant = grants[0]
        if grant is None:
            return None
        grant["requests_consumed"] += 1
        grant["requests_remaining"] -= 1
        if grant["requests_remaining"] <= 0:
            grant["status"] = "exhausted"
        grant["updated_at"] = datetime.now(UTC)
        await append_usage_ledger(
            {
                "id": f"led_{request_id[-12:]}",
                "api_key_id": grant["api_key_id"],
                "api_key_prefix": grant["api_key_prefix"],
                "quota_grant_id": grant["id"],
                "request_id": request_id,
                "operation": "consume",
                "delta": -1,
                "balance_after": grant["requests_remaining"],
                "reason": path,
                "metadata_json": {"grant_type": grant["grant_type"], "package_slug": grant.get("package_slug")},
                "created_at": datetime.now(UTC),
            }
        )
        return {"allowed": True, "remaining": grant["requests_remaining"], "grant_id": grant["id"]}
