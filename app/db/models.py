import enum
import uuid

from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

try:
    from geoalchemy2 import Geometry
except ModuleNotFoundError:  # pragma: no cover
    Geometry = None


class CoolingType(str, enum.Enum):
    DIRECT_EVAPORATIVE = "DIRECT_EVAPORATIVE"
    CLOSED_LOOP = "CLOSED_LOOP"
    ADIABATIC_HYBRID = "ADIABATIC_HYBRID"


class DataCenter(Base):
    __tablename__ = "datacenters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    region_slug: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    max_it_capacity_mw: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    pue: Mapped[float] = mapped_column(Float, nullable=False, default=1.25)
    cooling_type: Mapped[CoolingType] = mapped_column(Enum(CoolingType, name="cooling_type"), nullable=False)
    base_wue: Mapped[float] = mapped_column(Float, nullable=False, default=1.8)
    grid_zone_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    water_stress_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ping_target_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    if Geometry is not None:
        location = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    else:  # pragma: no cover
        location = mapped_column(String(128), nullable=True)


class RequestActivity(Base):
    __tablename__ = "request_activity"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(12), nullable=False)
    path: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False)
    client_ip: Mapped[str] = mapped_column(String(64), nullable=False)
    api_key_prefix: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    rate_limit_class: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    region: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class ManagedApiKeyRecord(Base):
    __tablename__ = "managed_api_keys"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    environment: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    allowed_endpoints: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    allowed_origins: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    allowed_ips: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    project_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    usage_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    prefix: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    hashed_key: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    actor: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    target: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    result: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    client_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class BillingPackage(Base):
    __tablename__ = "billing_packages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    requests_granted: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Integer, nullable=False, default=1)
    environment: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    package_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1")
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class BillingCheckoutSession(Base):
    __tablename__ = "billing_checkout_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    public_token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    target_api_key_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    target_api_key_prefix: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    package_slug: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="square")
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    requests_expected: Mapped[int] = mapped_column(Integer, nullable=False)
    checkout_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    square_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    square_payment_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class QuotaGrant(Base):
    __tablename__ = "quota_grants"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    api_key_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    api_key_prefix: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    checkout_session_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    package_slug: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    grant_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    requests_granted: Mapped[int] = mapped_column(Integer, nullable=False)
    requests_consumed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    requests_remaining: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class UsageLedgerEntry(Base):
    __tablename__ = "usage_ledger"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    api_key_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    api_key_prefix: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    quota_grant_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    operation: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(120), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class BillingProject(Base):
    __tablename__ = "billing_projects"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    environment: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    monthly_budget_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    soft_budget_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    owner_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class BillingSubscription(Base):
    __tablename__ = "billing_subscriptions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    plan_slug: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    plan_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    billing_cycle: Mapped[str] = mapped_column(String(20), nullable=False, default="monthly")
    included_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    monthly_price_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    renews_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
