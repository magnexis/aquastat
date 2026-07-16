from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.db.models import AuditEvent, ManagedApiKeyRecord, RequestActivity
from app.db.session import get_session_factory


async def save_request_activity(payload: dict[str, Any]) -> bool:
    try:
        factory = get_session_factory()
        async with factory() as session:
            session.add(
                RequestActivity(
                    id=payload["id"],
                    request_id=payload["request_id"],
                    method=payload["method"],
                    path=payload["path"],
                    status_code=payload["status_code"],
                    duration_ms=payload["duration_ms"],
                    client_ip=payload["client_ip"],
                    api_key_prefix=payload.get("api_key_prefix"),
                    rate_limit_class=payload["rate_limit_class"],
                    provider=payload.get("provider"),
                    region=payload.get("region"),
                    created_at=payload["created_at"],
                )
            )
            await session.commit()
        return True
    except (SQLAlchemyError, ModuleNotFoundError, OSError, RuntimeError, AttributeError, Exception):
        return False


async def list_request_activity(limit: int) -> list[dict[str, Any]] | None:
    try:
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(select(RequestActivity).order_by(RequestActivity.created_at.desc()).limit(limit))
            rows = result.scalars().all()
        return [
            {
                "id": row.id,
                "request_id": row.request_id,
                "timestamp": row.created_at,
                "method": row.method,
                "path": row.path,
                "status_code": row.status_code,
                "duration_ms": row.duration_ms,
                "client_ip": row.client_ip,
                "api_key_prefix": row.api_key_prefix,
                "rate_limit_class": row.rate_limit_class,
                "provider": row.provider,
                "region": row.region,
            }
            for row in rows
        ]
    except (SQLAlchemyError, ModuleNotFoundError, OSError, RuntimeError, AttributeError, Exception):
        return None


async def count_request_activity() -> int | None:
    rows = await list_request_activity(limit=10000)
    if rows is None:
        return None
    return len(rows)


async def save_managed_api_key(payload: dict[str, Any]) -> bool:
    try:
        factory = get_session_factory()
        async with factory() as session:
            session.add(
                ManagedApiKeyRecord(
                    id=payload["id"],
                    name=payload["name"],
                    description=payload.get("description"),
                    environment=payload["environment"],
                    scopes=payload.get("scopes", []),
                    allowed_endpoints=payload.get("allowed_endpoints", []),
                    allowed_origins=payload.get("allowed_origins", []),
                    allowed_ips=payload.get("allowed_ips", []),
                    usage_limit=payload.get("usage_limit"),
                    status=payload["status"],
                    prefix=payload["prefix"],
                    hashed_key=payload["hashed_key"],
                    created_at=payload["created_at"],
                    expires_at=payload.get("expires_at"),
                    last_used_at=payload.get("last_used_at"),
                )
            )
            await session.commit()
        return True
    except (SQLAlchemyError, ModuleNotFoundError, OSError, RuntimeError, AttributeError, Exception):
        return False


async def list_managed_api_keys() -> list[dict[str, Any]] | None:
    try:
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(ManagedApiKeyRecord).order_by(ManagedApiKeyRecord.created_at.desc())
            )
            rows = result.scalars().all()
        return [
            {
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "environment": row.environment,
                "scopes": row.scopes or [],
                "allowed_endpoints": row.allowed_endpoints or [],
                "allowed_origins": row.allowed_origins or [],
                "allowed_ips": row.allowed_ips or [],
                "usage_limit": row.usage_limit,
                "status": row.status,
                "prefix": row.prefix,
                "hashed_key": row.hashed_key,
                "created_at": row.created_at,
                "expires_at": row.expires_at,
                "last_used_at": row.last_used_at,
            }
            for row in rows
        ]
    except (SQLAlchemyError, ModuleNotFoundError, OSError, RuntimeError, AttributeError, Exception):
        return None


async def get_managed_api_key_by_hash(hashed_key: str) -> dict[str, Any] | None:
    try:
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(ManagedApiKeyRecord).where(ManagedApiKeyRecord.hashed_key == hashed_key)
            )
            row = result.scalar_one_or_none()
        if row is None:
            return None
        return {
            "id": row.id,
            "name": row.name,
            "description": row.description,
            "environment": row.environment,
            "scopes": row.scopes or [],
            "allowed_endpoints": row.allowed_endpoints or [],
            "allowed_origins": row.allowed_origins or [],
            "allowed_ips": row.allowed_ips or [],
            "usage_limit": row.usage_limit,
            "status": row.status,
            "prefix": row.prefix,
            "hashed_key": row.hashed_key,
            "created_at": row.created_at,
            "expires_at": row.expires_at,
            "last_used_at": row.last_used_at,
        }
    except (SQLAlchemyError, ModuleNotFoundError, OSError, RuntimeError, AttributeError, Exception):
        return None


async def update_managed_api_key_status(key_id: str, status: str) -> dict[str, Any] | None:
    try:
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(select(ManagedApiKeyRecord).where(ManagedApiKeyRecord.id == key_id))
            row = result.scalar_one_or_none()
            if row is None:
                return None
            row.status = status
            await session.commit()
            await session.refresh(row)
            return {
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "environment": row.environment,
                "scopes": row.scopes or [],
                "allowed_endpoints": row.allowed_endpoints or [],
                "allowed_origins": row.allowed_origins or [],
                "allowed_ips": row.allowed_ips or [],
                "usage_limit": row.usage_limit,
                "status": row.status,
                "prefix": row.prefix,
                "hashed_key": row.hashed_key,
                "created_at": row.created_at,
                "expires_at": row.expires_at,
                "last_used_at": row.last_used_at,
            }
    except (SQLAlchemyError, ModuleNotFoundError, OSError, RuntimeError, AttributeError, Exception):
        return None


async def save_audit_event(payload: dict[str, Any]) -> bool:
    try:
        factory = get_session_factory()
        async with factory() as session:
            session.add(
                AuditEvent(
                    id=payload["id"],
                    actor=payload["actor"],
                    action=payload["action"],
                    target=payload["target"],
                    result=payload["result"],
                    request_id=payload.get("request_id"),
                    client_ip=payload.get("client_ip"),
                    metadata_json=payload.get("metadata_json", {}),
                    created_at=payload.get("created_at", datetime.now(UTC)),
                )
            )
            await session.commit()
        return True
    except (SQLAlchemyError, ModuleNotFoundError, OSError, RuntimeError, AttributeError, Exception):
        return False


async def list_audit_events(limit: int) -> list[dict[str, Any]] | None:
    try:
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit))
            rows = result.scalars().all()
        return [
            {
                "id": row.id,
                "actor": row.actor,
                "action": row.action,
                "target": row.target,
                "result": row.result,
                "request_id": row.request_id,
                "client_ip": row.client_ip,
                "metadata_json": row.metadata_json or {},
                "created_at": row.created_at,
            }
            for row in rows
        ]
    except (SQLAlchemyError, ModuleNotFoundError, OSError, RuntimeError, AttributeError, Exception):
        return None
