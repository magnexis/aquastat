CREATE EXTENSION IF NOT EXISTS postgis;

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

CREATE TABLE IF NOT EXISTS datacenters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(50) NOT NULL,
    region_slug VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    location GEOMETRY(Point, 4326) NOT NULL,
    max_it_capacity_mw DOUBLE PRECISION NOT NULL DEFAULT 50.0,
    cooling_type cooling_system_type NOT NULL DEFAULT 'DIRECT_EVAPORATIVE',
    base_wue DOUBLE PRECISION NOT NULL DEFAULT 1.8,
    pue DOUBLE PRECISION NOT NULL DEFAULT 1.25,
    water_stress_score NUMERIC(3, 2) NOT NULL DEFAULT 1.00,
    grid_zone_id VARCHAR(50) NOT NULL,
    ping_target_ip VARCHAR(45),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_datacenters_geom ON datacenters USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_datacenters_provider_region ON datacenters(provider, region_slug);

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
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_request_activity_created_at ON request_activity(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_request_activity_path ON request_activity(path);
CREATE INDEX IF NOT EXISTS idx_request_activity_request_id ON request_activity(request_id);

CREATE TABLE IF NOT EXISTS managed_api_keys (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    environment VARCHAR(20) NOT NULL,
    scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
    allowed_endpoints JSONB NOT NULL DEFAULT '[]'::jsonb,
    allowed_origins JSONB NOT NULL DEFAULT '[]'::jsonb,
    allowed_ips JSONB NOT NULL DEFAULT '[]'::jsonb,
    usage_limit INTEGER,
    status VARCHAR(20) NOT NULL,
    prefix VARCHAR(20) NOT NULL,
    hashed_key VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_managed_api_keys_created_at ON managed_api_keys(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_managed_api_keys_prefix ON managed_api_keys(prefix);
CREATE INDEX IF NOT EXISTS idx_managed_api_keys_status ON managed_api_keys(status);

CREATE TABLE IF NOT EXISTS audit_events (
    id VARCHAR(32) PRIMARY KEY,
    actor VARCHAR(128) NOT NULL,
    action VARCHAR(80) NOT NULL,
    target VARCHAR(128) NOT NULL,
    result VARCHAR(32) NOT NULL,
    request_id VARCHAR(128),
    client_ip VARCHAR(64),
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_events_created_at ON audit_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_action ON audit_events(action);
CREATE INDEX IF NOT EXISTS idx_audit_events_target ON audit_events(target);

INSERT INTO datacenters (
    provider,
    region_slug,
    name,
    latitude,
    longitude,
    location,
    max_it_capacity_mw,
    cooling_type,
    base_wue,
    pue,
    water_stress_score,
    grid_zone_id,
    ping_target_ip
)
VALUES
    (
        'AWS',
        'us-east-1',
        'Northern Virginia Campus',
        39.0438,
        -77.4874,
        ST_SetSRID(ST_MakePoint(-77.4874, 39.0438), 4326),
        150.0,
        'DIRECT_EVAPORATIVE',
        1.8,
        1.21,
        2.4,
        'US-MIDA-PJM',
        '15.230.0.0'
    ),
    (
        'AWS',
        'us-west-2',
        'Oregon Campus (Water-Smart)',
        45.8412,
        -119.7001,
        ST_SetSRID(ST_MakePoint(-119.7001, 45.8412), 4326),
        100.0,
        'CLOSED_LOOP',
        0.19,
        1.12,
        4.1,
        'US-NW-PACW',
        '52.119.128.0'
    ),
    (
        'GCP',
        'europe-west1',
        'St. Ghislain, Belgium',
        50.4712,
        3.8251,
        ST_SetSRID(ST_MakePoint(3.8251, 50.4712), 4326),
        80.0,
        'ADIABATIC_HYBRID',
        1.4,
        1.16,
        1.2,
        'BE',
        '8.8.8.8'
    )
ON CONFLICT (region_slug) DO NOTHING;
