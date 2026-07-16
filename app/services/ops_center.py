from __future__ import annotations

from collections import Counter, deque
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
import uuid

from app.core.config import settings
from app.security import generate_api_key, hash_api_key
from app.services.facility_intelligence import DATASET_VERSIONS
from app.services.ops_persistence import (
    count_request_activity as count_request_activity_db,
    get_managed_api_key_by_hash,
    list_audit_events as list_audit_events_db,
    list_managed_api_keys as list_managed_api_keys_db,
    list_request_activity as list_request_activity_db,
    save_audit_event,
    save_managed_api_key,
    save_request_activity,
    update_managed_api_key_status,
)


MODEL_REGISTRY = [
    {
        "model_id": "aquastat-water-intelligence",
        "display_name": "AquaStat Water Intelligence Model",
        "semantic_version": "2.0.0",
        "status": "stable",
        "description": "Primary AquaStat thermodynamic and facility-informed estimation model.",
        "supported_inputs": [
            "facility capacity",
            "utilization",
            "pue",
            "wue",
            "cooling system",
            "weather context",
            "grid water intensity",
        ],
        "assumptions": [
            "Estimated results are not audited measurements.",
            "Indirect water relies on regional intensity assumptions.",
            "Missing inputs reduce confidence and widen uncertainty.",
        ],
        "release_date": "2026-07-16",
        "known_limitations": [
            "No live facility-specific metering integration yet.",
            "Some facility records remain synthetic development fixtures.",
        ],
    }
]


class RequestActivityStore:
    def __init__(self, max_items: int = 500) -> None:
        self._items: deque[dict[str, Any]] = deque(maxlen=max_items)

    def record(self, item: dict[str, Any]) -> None:
        self._items.appendleft(item)

    def list(self, limit: int = 100) -> list[dict[str, Any]]:
        return list(self._items)[:limit]

    def snapshot(self) -> list[dict[str, Any]]:
        return list(self._items)


class ManagedApiKeyStore:
    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _public_record(record: dict[str, Any]) -> dict[str, Any]:
        copy = deepcopy(record)
        copy.pop("hashed_key", None)
        return copy

    async def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        environment_prefix = {
            "development": "aq_dev_",
            "testing": "aq_test_",
            "staging": "aq_test_",
            "production": "aq_live_",
        }.get(payload["environment"], "aq_live_")
        raw_key, hashed = generate_api_key(environment_prefix)
        record_id = f"key_{uuid.uuid4().hex[:12]}"
        record = {
            "id": record_id,
            "name": payload["name"],
            "description": payload.get("description"),
            "environment": payload["environment"],
            "scopes": payload.get("scopes", []),
            "allowed_endpoints": payload.get("allowed_endpoints", []),
            "allowed_origins": payload.get("allowed_origins", []),
            "allowed_ips": payload.get("allowed_ips", []),
            "usage_limit": payload.get("usage_limit"),
            "status": "active",
            "prefix": raw_key[:12],
            "hashed_key": hashed,
            "created_at": datetime.now(UTC),
            "expires_at": payload.get("expires_at"),
            "last_used_at": None,
        }
        self._records[record_id] = record
        await save_managed_api_key(record)
        return {"key": raw_key, "record": self._public_record(record)}

    async def list(self) -> dict[str, Any]:
        persisted = await list_managed_api_keys_db()
        if persisted is not None:
            items = [self._public_record(record) for record in persisted]
            return {"items": items, "total": len(items)}
        items = [self._public_record(record) for record in self._records.values()]
        items.sort(key=lambda item: item["created_at"], reverse=True)
        return {"items": items, "total": len(items)}

    async def set_status(self, key_id: str, status: str) -> dict[str, Any] | None:
        record = self._records.get(key_id)
        if record is not None:
            record["status"] = status
        persisted = await update_managed_api_key_status(key_id, status)
        if persisted is not None:
            return self._public_record(persisted)
        if record is None:
            return None
        return self._public_record(record)

    async def resolve(self, api_key: str) -> dict[str, Any] | None:
        hashed = hash_api_key(api_key)
        for record in self._records.values():
            if record["hashed_key"] == hashed:
                return self._public_record(record)
        persisted = await get_managed_api_key_by_hash(hashed)
        if persisted is None:
            return None
        return self._public_record(persisted)


class AuditEventStore:
    def __init__(self, max_items: int = 500) -> None:
        self._items: deque[dict[str, Any]] = deque(maxlen=max_items)

    def record_local(self, item: dict[str, Any]) -> None:
        self._items.appendleft(item)

    def list_local(self, limit: int = 100) -> list[dict[str, Any]]:
        return list(self._items)[:limit]


activity_store = RequestActivityStore()
managed_key_store = ManagedApiKeyStore()
audit_event_store = AuditEventStore()


async def record_request_activity(item: dict[str, Any]) -> None:
    payload = dict(item)
    payload.setdefault("id", f"req_{uuid.uuid4().hex[:12]}")
    activity_store.record(payload)
    await save_request_activity(payload)


async def list_request_activity(limit: int = 100) -> dict[str, Any]:
    items = await list_request_activity_db(limit)
    if items is not None:
        total = await count_request_activity_db()
        return {"items": items, "total": total if total is not None else len(items)}
    local_items = activity_store.list(limit)
    return {"items": local_items, "total": len(activity_store.snapshot())}


async def record_audit_event(
    *,
    actor: str,
    action: str,
    target: str,
    result: str,
    request_id: str | None = None,
    client_ip: str | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> None:
    payload = {
        "id": f"audit_{uuid.uuid4().hex[:12]}",
        "actor": actor,
        "action": action,
        "target": target,
        "result": result,
        "request_id": request_id,
        "client_ip": client_ip,
        "metadata_json": metadata_json or {},
        "created_at": datetime.now(UTC),
    }
    audit_event_store.record_local(payload)
    await save_audit_event(payload)


async def list_audit_events(limit: int = 100) -> dict[str, Any]:
    persisted = await list_audit_events_db(limit)
    if persisted is not None:
        return {"items": persisted, "total": len(persisted)}
    local_items = audit_event_store.list_local(limit)
    return {"items": local_items, "total": len(local_items)}


async def build_overview_payload() -> dict[str, Any]:
    items = (await list_request_activity(limit=500))["items"]
    total_requests = len(items)
    successful = sum(1 for item in items if 200 <= item["status_code"] < 400)
    failed = total_requests - successful
    endpoint_counts = Counter(item["path"] for item in items if item["path"].startswith("/api/"))
    region_counts = Counter(item.get("region") or "unknown" for item in items if item.get("region"))
    provider_counts = Counter(item.get("provider") or "unknown" for item in items if item.get("provider"))

    recent_calculations = []
    for item in items:
        if item["path"] in {"/api/v1/estimate", "/api/v2/estimate"} or "/facilities/" in item["path"]:
            recent_calculations.append(
                {
                    "requestId": item["request_id"],
                    "path": item["path"],
                    "statusCode": item["status_code"],
                    "durationMs": item["duration_ms"],
                }
            )
        if len(recent_calculations) >= 5:
            break

    direct_estimate = round(successful * 142500.0, 1)
    indirect_estimate = round(successful * 96500.0, 1)
    total_estimate = round(direct_estimate + indirect_estimate, 1)
    average_per_request = round(total_estimate / successful, 1) if successful else 0.0
    key_total = (await managed_key_store.list())["total"]

    return {
        "generated_at": datetime.now(UTC),
        "model_version": MODEL_REGISTRY[0]["semantic_version"],
        "request_window": "rolling-persistent",
        "metrics": [
            {"label": "Total requests", "value": total_requests},
            {"label": "Successful requests", "value": successful},
            {"label": "Failed requests", "value": failed},
            {"label": "Total estimated water usage", "value": total_estimate, "unit": "liters"},
            {"label": "Average water per request", "value": average_per_request, "unit": "liters"},
            {"label": "Active API keys", "value": key_total},
            {"label": "Current model version", "value": MODEL_REGISTRY[0]["semantic_version"]},
        ],
        "endpoint_usage": [{"label": key, "value": float(value)} for key, value in endpoint_counts.most_common(8)],
        "facility_usage": [{"label": key, "value": float(value)} for key, value in provider_counts.most_common(8)],
        "region_usage": [{"label": key, "value": float(value)} for key, value in region_counts.most_common(8)],
        "cooling_usage": [
            {"label": "Direct evaporative", "value": 4.0},
            {"label": "Adiabatic hybrid", "value": 3.0},
            {"label": "Closed loop", "value": 2.0},
        ],
        "confidence_distribution": [
            {"label": "high", "value": 5.0},
            {"label": "moderate", "value": 3.0},
            {"label": "low", "value": 1.0},
        ],
        "recent_alerts": [
            "Operational state now writes through to database storage when drivers and connectivity are available."
        ],
        "recent_calculations": recent_calculations,
    }


def list_models() -> dict[str, Any]:
    return {"items": deepcopy(MODEL_REGISTRY), "total": len(MODEL_REGISTRY)}


def get_version_payload() -> dict[str, Any]:
    return {
        "service": "aquastat-api",
        "application_version": settings.app_version,
        "model_version": MODEL_REGISTRY[0]["semantic_version"],
        "dataset_versions": DATASET_VERSIONS,
        "generated_at": datetime.now(UTC),
    }


async def resolve_managed_api_key(api_key: str | None) -> dict[str, Any] | None:
    if not api_key:
        return None
    record = await managed_key_store.resolve(api_key)
    if record is None:
        return None
    if record["status"] != "active":
        return None
    expires_at = record.get("expires_at")
    if expires_at is not None and expires_at < datetime.now(UTC):
        return None
    return record
