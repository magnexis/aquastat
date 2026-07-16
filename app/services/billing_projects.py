from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from io import StringIO
import csv
import uuid

from fastapi import HTTPException, status

from app.core.config import settings
from app.services.billing_persistence import (
    append_usage_ledger,
    list_project_subscriptions_db,
    list_projects_db,
    list_quota_grants,
    list_usage_ledger_db,
    save_project_db,
    save_subscription_db,
)
from app.services.ops_center import managed_key_store


@dataclass
class ProjectPlan:
    slug: str
    name: str
    monthly_price_minor: int
    included_requests: int
    soft_budget_minor: int | None
    monthly_budget_minor: int | None


DEFAULT_PROJECT_PLANS = [
    ProjectPlan("free", "Free", 0, 1_000, 0, 0),
    ProjectPlan("developer", "Developer", 2_900, 25_000, 2_500, 4_000),
    ProjectPlan("pro", "Pro", 14_900, 150_000, 12_500, 18_000),
    ProjectPlan("business", "Business", 49_900, 750_000, 40_000, 60_000),
]

_projects: dict[str, dict] = {}
_subscriptions: dict[str, dict] = {}


def _slugify(name: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in name).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or f"project-{uuid.uuid4().hex[:6]}"


async def _seed_default_project() -> None:
    persisted = await list_projects_db()
    existing = persisted if persisted else list(_projects.values())
    if existing:
        if persisted:
            _projects.clear()
            for item in persisted:
                _projects[item["id"]] = item
        return
    await create_project(
        name="Default Project",
        environment=settings.environment,
        description="Default AquaStat project for standalone API keys.",
        plan_slug="free",
        owner_email=None,
    )


async def list_projects() -> list[dict]:
    await _seed_default_project()
    persisted = await list_projects_db()
    if persisted is not None and persisted:
        _projects.clear()
        for item in persisted:
            _projects[item["id"]] = item
        return list(_projects.values())
    return list(_projects.values())


async def list_subscriptions() -> list[dict]:
    persisted = await list_project_subscriptions_db()
    if persisted is not None and persisted:
        _subscriptions.clear()
        for item in persisted:
            _subscriptions[item["id"]] = item
        return list(_subscriptions.values())
    return list(_subscriptions.values())


async def create_project(
    *,
    name: str,
    environment: str,
    description: str | None,
    plan_slug: str,
    owner_email: str | None,
) -> dict:
    now = datetime.now(UTC)
    plan = next((item for item in DEFAULT_PROJECT_PLANS if item.slug == plan_slug), None)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing plan not found")

    project_id = f"prj_{uuid.uuid4().hex[:12]}"
    project = {
        "id": project_id,
        "name": name,
        "slug": _slugify(name),
        "description": description,
        "environment": environment,
        "status": "active",
        "monthly_budget_minor": plan.monthly_budget_minor,
        "soft_budget_minor": plan.soft_budget_minor,
        "currency": settings.billing_default_currency,
        "owner_email": owner_email,
        "metadata_json": {"plan_slug": plan.slug},
        "created_at": now,
        "updated_at": now,
    }
    subscription = {
        "id": f"sub_{uuid.uuid4().hex[:12]}",
        "project_id": project_id,
        "plan_slug": plan.slug,
        "plan_name": plan.name,
        "status": "active",
        "billing_cycle": "monthly",
        "included_requests": plan.included_requests,
        "monthly_price_minor": plan.monthly_price_minor,
        "currency": settings.billing_default_currency,
        "starts_at": now,
        "renews_at": now + timedelta(days=30),
        "canceled_at": None,
        "metadata_json": {},
        "created_at": now,
        "updated_at": now,
    }
    _projects[project_id] = project
    _subscriptions[subscription["id"]] = subscription
    await save_project_db(project)
    await save_subscription_db(subscription)
    return {
        **project,
        "subscription": subscription,
    }


async def get_project(project_id: str) -> dict:
    for project in await list_projects():
        if project["id"] == project_id:
            subscription = next((item for item in await list_subscriptions() if item["project_id"] == project_id), None)
            return {**project, "subscription": subscription}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing project not found")


async def _keys_for_project(project_id: str) -> list[dict]:
    listing = await managed_key_store.list()
    return [item for item in listing["items"] if item.get("project_id") == project_id]


async def project_usage_summary(project_id: str) -> dict:
    project = await get_project(project_id)
    subscription = project.get("subscription")
    keys = await _keys_for_project(project_id)
    ledger: list[dict] = []
    for key in keys:
        key_ledger = await list_usage_ledger_db(api_key_id=key["id"])
        if key_ledger:
            ledger.extend(key_ledger)
    ledger.sort(key=lambda item: item["created_at"], reverse=True)

    totals = defaultdict(int)
    for item in ledger or []:
        if item["operation"] == "consume":
            totals["consumed"] += abs(int(item["delta"]))
        elif item["operation"] == "grant":
            if item.get("grant_type") == "included":
                totals["included_granted"] += int(item["delta"])
            else:
                totals["prepaid_granted"] += int(item["delta"])

    included_requests = int(subscription["included_requests"]) if subscription else 0
    prepaid_remaining = 0
    for key in keys:
        grants = await list_quota_grants(key["id"])
        if grants:
            prepaid_remaining += sum(
                int(item["requests_remaining"])
                for item in grants
                if item["grant_type"] != "included" and item["status"] in {"active", "exhausted"}
            )
    consumed_requests = int(totals["consumed"])
    estimated_spend_minor = 0
    if subscription:
        rate = subscription["monthly_price_minor"] / max(subscription["included_requests"], 1)
        estimated_spend_minor = int(round(consumed_requests * rate))

    monthly_budget_minor = project.get("monthly_budget_minor")
    soft_budget_minor = project.get("soft_budget_minor")
    budget_state = "within_budget"
    if monthly_budget_minor is not None and estimated_spend_minor >= monthly_budget_minor:
        budget_state = "hard_limit_reached"
    elif soft_budget_minor is not None and estimated_spend_minor >= soft_budget_minor:
        budget_state = "soft_limit_warning"

    low_credit_threshold_requests = max(10, int((included_requests or 0) * 0.1))
    low_credit = prepaid_remaining > 0 and prepaid_remaining <= low_credit_threshold_requests
    alerts: list[dict] = []
    if budget_state == "hard_limit_reached":
        alerts.append(
            {
                "code": "PROJECT_BUDGET_HARD_LIMIT",
                "severity": "high",
                "message": f"{project['name']} has reached its configured monthly budget ceiling.",
                "project_id": project_id,
            }
        )
    elif budget_state == "soft_limit_warning":
        alerts.append(
            {
                "code": "PROJECT_BUDGET_SOFT_LIMIT",
                "severity": "medium",
                "message": f"{project['name']} is approaching its configured monthly budget.",
                "project_id": project_id,
            }
        )
    if low_credit:
        alerts.append(
            {
                "code": "PROJECT_PREPAID_LOW_CREDIT",
                "severity": "medium",
                "message": f"{project['name']} has low prepaid request credit remaining.",
                "project_id": project_id,
            }
        )

    return {
        "project": {
            "id": project["id"],
            "name": project["name"],
            "slug": project["slug"],
            "environment": project["environment"],
            "status": project["status"],
        },
        "subscription": subscription,
        "keys_total": len(keys),
        "keys": keys,
        "usage": {
            "included_requests": included_requests,
            "prepaid_remaining_requests": prepaid_remaining,
            "consumed_requests": consumed_requests,
            "estimated_spend_minor": estimated_spend_minor,
            "currency": project["currency"],
            "monthly_budget_minor": monthly_budget_minor,
            "soft_budget_minor": soft_budget_minor,
            "budget_state": budget_state,
            "low_credit_threshold_requests": low_credit_threshold_requests,
            "low_credit": low_credit,
        },
        "alerts": alerts,
        "usage_activity": ledger or [],
    }


async def grant_prepaid_refill(
    project_id: str,
    api_key_id: str,
    package_slug: str,
    requests_granted: int,
    checkout_session_id: str | None = None,
) -> dict:
    project = await get_project(project_id)
    key_record = next((item for item in (await _keys_for_project(project_id)) if item["id"] == api_key_id), None)
    if key_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Managed API key not found for billing project")

    now = datetime.now(UTC)
    grant_id = f"grt_{uuid.uuid4().hex[:12]}"
    payload = {
        "id": grant_id,
        "api_key_id": api_key_id,
        "api_key_prefix": key_record["prefix"],
        "checkout_session_id": checkout_session_id,
        "package_slug": package_slug,
        "grant_type": "prepaid",
        "requests_granted": requests_granted,
        "requests_consumed": 0,
        "requests_remaining": requests_granted,
        "status": "active",
        "starts_at": now,
        "expires_at": None,
        "revoked_at": None,
        "revocation_reason": None,
        "created_at": now,
        "updated_at": now,
    }
    from app.services.billing_persistence import save_quota_grant

    await save_quota_grant(payload)
    await append_usage_ledger(
        {
            "id": f"led_{uuid.uuid4().hex[:12]}",
            "api_key_id": api_key_id,
            "api_key_prefix": key_record["prefix"],
            "quota_grant_id": grant_id,
            "request_id": None,
            "operation": "grant",
            "delta": requests_granted,
            "balance_after": requests_granted,
            "reason": f"project:{project_id}:{package_slug}",
            "metadata_json": {
                "project_id": project_id,
                "grant_type": "prepaid",
                "package_slug": package_slug,
                "checkout_session_id": checkout_session_id,
            },
            "created_at": now,
        }
    )
    return {"project_id": project["id"], "api_key_id": api_key_id, "grant_id": grant_id, "requests_granted": requests_granted}


async def export_project_usage_csv(project_id: str) -> str:
    summary = await project_usage_summary(project_id)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "project_id",
            "project_name",
            "api_key_id",
            "api_key_prefix",
            "operation",
            "delta",
            "balance_after",
            "reason",
            "created_at",
        ]
    )
    for item in summary["usage_activity"]:
        writer.writerow(
            [
                project_id,
                summary["project"]["name"],
                item["api_key_id"],
                item["api_key_prefix"],
                item["operation"],
                item["delta"],
                item["balance_after"],
                item["reason"],
                item["created_at"].isoformat(),
            ]
        )
    return output.getvalue()
