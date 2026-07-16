from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.seeds import SEED_DATACENTERS
from app.db.session import get_engine


async def bootstrap_database() -> None:
    if not settings.bootstrap_database_on_startup:
        return

    try:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            await conn.execute(
                text(
                    """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'cooling_system_type') THEN
                            CREATE TYPE cooling_system_type AS ENUM (
                                'DIRECT_EVAPORATIVE',
                                'CLOSED_LOOP',
                                'ADIABATIC_HYBRID'
                            );
                        END IF;
                    END $$;
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS datacenters (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        name VARCHAR(255) NOT NULL,
                        provider VARCHAR(50) NOT NULL,
                        region_slug VARCHAR(50) NOT NULL UNIQUE,
                        latitude DOUBLE PRECISION NOT NULL,
                        longitude DOUBLE PRECISION NOT NULL,
                        geom GEOMETRY(Point, 4326),
                        max_it_capacity_mw DOUBLE PRECISION NOT NULL DEFAULT 50.0,
                        pue DOUBLE PRECISION NOT NULL DEFAULT 1.25,
                        cooling_type cooling_system_type NOT NULL DEFAULT 'DIRECT_EVAPORATIVE',
                        base_wue DOUBLE PRECISION NOT NULL DEFAULT 1.8,
                        grid_zone_id VARCHAR(50),
                        water_stress_score DOUBLE PRECISION,
                        ping_target_ip VARCHAR(45)
                    )
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS request_activity (
                        id VARCHAR(32) PRIMARY KEY,
                        request_id VARCHAR(128) NOT NULL,
                        method VARCHAR(12) NOT NULL,
                        path VARCHAR(255) NOT NULL,
                        status_code INTEGER NOT NULL,
                        duration_ms DOUBLE PRECISION NOT NULL,
                        client_ip VARCHAR(64) NOT NULL,
                        api_key_prefix VARCHAR(20),
                        rate_limit_class VARCHAR(32) NOT NULL,
                        provider VARCHAR(64),
                        region VARCHAR(128),
                        created_at TIMESTAMPTZ NOT NULL
                    )
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS managed_api_keys (
                        id VARCHAR(32) PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        description TEXT,
                        environment VARCHAR(20) NOT NULL,
                        scopes JSON NOT NULL,
                        allowed_endpoints JSON NOT NULL,
                        allowed_origins JSON NOT NULL,
                        allowed_ips JSON NOT NULL,
                        project_id VARCHAR(32),
                        usage_limit INTEGER,
                        status VARCHAR(20) NOT NULL,
                        prefix VARCHAR(20) NOT NULL,
                        hashed_key VARCHAR(128) NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        expires_at TIMESTAMPTZ,
                        last_used_at TIMESTAMPTZ
                    )
                    """
                )
            )
            await conn.execute(text("ALTER TABLE managed_api_keys ADD COLUMN IF NOT EXISTS project_id VARCHAR(32)"))
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS audit_events (
                        id VARCHAR(32) PRIMARY KEY,
                        actor VARCHAR(128) NOT NULL,
                        action VARCHAR(80) NOT NULL,
                        target VARCHAR(128) NOT NULL,
                        result VARCHAR(32) NOT NULL,
                        request_id VARCHAR(128),
                        client_ip VARCHAR(64),
                        metadata_json JSON NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL
                    )
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS billing_projects (
                        id VARCHAR(32) PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        slug VARCHAR(100) NOT NULL UNIQUE,
                        description TEXT,
                        environment VARCHAR(20) NOT NULL,
                        status VARCHAR(20) NOT NULL,
                        monthly_budget_minor INTEGER,
                        soft_budget_minor INTEGER,
                        currency VARCHAR(8) NOT NULL DEFAULT 'USD',
                        owner_email VARCHAR(255),
                        metadata_json JSON NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL
                    )
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS billing_subscriptions (
                        id VARCHAR(32) PRIMARY KEY,
                        project_id VARCHAR(32) NOT NULL,
                        plan_slug VARCHAR(64) NOT NULL,
                        plan_name VARCHAR(100) NOT NULL,
                        status VARCHAR(20) NOT NULL,
                        billing_cycle VARCHAR(20) NOT NULL DEFAULT 'monthly',
                        included_requests INTEGER NOT NULL DEFAULT 0,
                        monthly_price_minor INTEGER NOT NULL DEFAULT 0,
                        currency VARCHAR(8) NOT NULL DEFAULT 'USD',
                        starts_at TIMESTAMPTZ NOT NULL,
                        renews_at TIMESTAMPTZ,
                        canceled_at TIMESTAMPTZ,
                        metadata_json JSON NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL
                    )
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS billing_packages (
                        id VARCHAR(32) PRIMARY KEY,
                        slug VARCHAR(64) NOT NULL UNIQUE,
                        name VARCHAR(100) NOT NULL,
                        description TEXT,
                        amount_minor INTEGER NOT NULL,
                        currency VARCHAR(8) NOT NULL,
                        requests_granted INTEGER NOT NULL,
                        active INTEGER NOT NULL DEFAULT 1,
                        environment VARCHAR(20) NOT NULL,
                        display_order INTEGER NOT NULL DEFAULT 0,
                        package_version VARCHAR(20) NOT NULL DEFAULT '1',
                        metadata_json JSON NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL
                    )
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS billing_checkout_sessions (
                        id VARCHAR(32) PRIMARY KEY,
                        public_token VARCHAR(64) NOT NULL UNIQUE,
                        target_api_key_id VARCHAR(32) NOT NULL,
                        target_api_key_prefix VARCHAR(20) NOT NULL,
                        package_slug VARCHAR(64) NOT NULL,
                        provider VARCHAR(32) NOT NULL DEFAULT 'square',
                        status VARCHAR(32) NOT NULL,
                        amount_minor INTEGER NOT NULL,
                        currency VARCHAR(8) NOT NULL,
                        requests_expected INTEGER NOT NULL,
                        checkout_url TEXT,
                        idempotency_key VARCHAR(128) NOT NULL UNIQUE,
                        square_order_id VARCHAR(128),
                        square_payment_id VARCHAR(128),
                        expires_at TIMESTAMPTZ,
                        completed_at TIMESTAMPTZ,
                        failed_at TIMESTAMPTZ,
                        canceled_at TIMESTAMPTZ,
                        created_at TIMESTAMPTZ NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL
                    )
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS quota_grants (
                        id VARCHAR(32) PRIMARY KEY,
                        api_key_id VARCHAR(32) NOT NULL,
                        api_key_prefix VARCHAR(20) NOT NULL,
                        checkout_session_id VARCHAR(32),
                        package_slug VARCHAR(64),
                        grant_type VARCHAR(32) NOT NULL,
                        requests_granted INTEGER NOT NULL,
                        requests_consumed INTEGER NOT NULL DEFAULT 0,
                        requests_remaining INTEGER NOT NULL,
                        status VARCHAR(20) NOT NULL,
                        starts_at TIMESTAMPTZ NOT NULL,
                        expires_at TIMESTAMPTZ,
                        revoked_at TIMESTAMPTZ,
                        revocation_reason TEXT,
                        created_at TIMESTAMPTZ NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL
                    )
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS usage_ledger (
                        id VARCHAR(32) PRIMARY KEY,
                        api_key_id VARCHAR(32) NOT NULL,
                        api_key_prefix VARCHAR(20) NOT NULL,
                        quota_grant_id VARCHAR(32),
                        request_id VARCHAR(128),
                        operation VARCHAR(32) NOT NULL,
                        delta INTEGER NOT NULL,
                        balance_after INTEGER NOT NULL,
                        reason VARCHAR(120) NOT NULL,
                        metadata_json JSON NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL
                    )
                    """
                )
            )

            for item in SEED_DATACENTERS:
                await conn.execute(
                    text(
                        """
                        INSERT INTO datacenters (
                            id, name, provider, region_slug, latitude, longitude, geom,
                            max_it_capacity_mw, pue, cooling_type, base_wue, grid_zone_id,
                            water_stress_score, ping_target_ip
                        )
                        VALUES (
                            :id, :name, :provider, :region_slug, :latitude, :longitude,
                            ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326),
                            :max_it_capacity_mw, :pue, CAST(:cooling_type AS cooling_system_type),
                            :base_wue, :grid_zone_id, :water_stress_score, :ping_target_ip
                        )
                        ON CONFLICT (id) DO NOTHING
                        """
                    ),
                    {
                        "id": str(item["id"]),
                        "name": item["name"],
                        "provider": item["provider"],
                        "region_slug": item["region_slug"],
                        "latitude": item["latitude"],
                        "longitude": item["longitude"],
                        "max_it_capacity_mw": item["max_it_capacity_mw"],
                        "pue": item["pue"],
                        "cooling_type": item["cooling_type"].value,
                        "base_wue": item["base_wue"],
                        "grid_zone_id": item["grid_zone_id"],
                        "water_stress_score": item["water_stress_score"],
                        "ping_target_ip": item["ping_target_ip"],
                    },
                )
    except SQLAlchemyError:
        return
    except ModuleNotFoundError:
        return
