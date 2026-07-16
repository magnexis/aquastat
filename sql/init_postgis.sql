CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS datacenters (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    provider VARCHAR(64) NOT NULL,
    region_slug VARCHAR(128) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    max_it_capacity_mw DOUBLE PRECISION NOT NULL DEFAULT 100.0,
    pue DOUBLE PRECISION NOT NULL DEFAULT 1.25,
    cooling_type VARCHAR(32) NOT NULL,
    base_wue DOUBLE PRECISION NOT NULL DEFAULT 1.8,
    location geometry(POINT, 4326)
);

CREATE INDEX IF NOT EXISTS idx_datacenters_provider_region
    ON datacenters (provider, region_slug);

INSERT INTO datacenters (
    id,
    name,
    provider,
    region_slug,
    latitude,
    longitude,
    max_it_capacity_mw,
    pue,
    cooling_type,
    base_wue,
    location
)
VALUES
    (
        '11111111-1111-4111-8111-111111111111',
        'AWS us-east-1a',
        'AWS',
        'us-east-1',
        39.0438,
        -77.4874,
        120.0,
        1.21,
        'DIRECT_EVAPORATIVE',
        1.8,
        ST_SetSRID(ST_MakePoint(-77.4874, 39.0438), 4326)
    ),
    (
        '22222222-2222-4222-8222-222222222222',
        'AWS eu-west-1',
        'AWS',
        'eu-west-1',
        53.3498,
        -6.2603,
        90.0,
        1.16,
        'ADIABATIC_HYBRID',
        1.6,
        ST_SetSRID(ST_MakePoint(-6.2603, 53.3498), 4326)
    ),
    (
        '33333333-3333-4333-8333-333333333333',
        'AWS eu-central-1',
        'AWS',
        'eu-central-1',
        50.1109,
        8.6821,
        100.0,
        1.18,
        'CLOSED_LOOP',
        1.4,
        ST_SetSRID(ST_MakePoint(8.6821, 50.1109), 4326)
    ),
    (
        '44444444-4444-4444-8444-444444444444',
        'GCP asia-southeast1',
        'GCP',
        'asia-southeast1',
        1.3521,
        103.8198,
        110.0,
        1.24,
        'DIRECT_EVAPORATIVE',
        2.0,
        ST_SetSRID(ST_MakePoint(103.8198, 1.3521), 4326)
    ),
    (
        '55555555-5555-4555-8555-555555555555',
        'Azure us-west-2',
        'Azure',
        'us-west-2',
        45.5152,
        -122.6784,
        95.0,
        1.20,
        'ADIABATIC_HYBRID',
        1.7,
        ST_SetSRID(ST_MakePoint(-122.6784, 45.5152), 4326)
    )
ON CONFLICT (id) DO NOTHING;
