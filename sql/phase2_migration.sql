CREATE EXTENSION IF NOT EXISTS postgis;

ALTER TABLE datacenters ADD COLUMN IF NOT EXISTS geom GEOMETRY(Point, 4326);
ALTER TABLE datacenters ADD COLUMN IF NOT EXISTS grid_zone_id VARCHAR(50);
ALTER TABLE datacenters ADD COLUMN IF NOT EXISTS water_stress_score NUMERIC(3, 2);
ALTER TABLE datacenters ADD COLUMN IF NOT EXISTS ping_target_ip VARCHAR(45);
ALTER TABLE datacenters ADD COLUMN IF NOT EXISTS pue DOUBLE PRECISION NOT NULL DEFAULT 1.25;

UPDATE datacenters
SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
WHERE geom IS NULL;

CREATE INDEX IF NOT EXISTS idx_datacenters_geom
    ON datacenters USING GIST(geom);

CREATE TABLE IF NOT EXISTS seasonal_baselines (
    region_slug VARCHAR(128) PRIMARY KEY,
    dry_bulb_temp_c DOUBLE PRECISION NOT NULL,
    relative_humidity_pct DOUBLE PRECISION NOT NULL,
    grid_load_factor DOUBLE PRECISION NOT NULL,
    carbon_intensity_g_per_kwh DOUBLE PRECISION NOT NULL,
    latency_factor DOUBLE PRECISION NOT NULL,
    jitter_ms DOUBLE PRECISION NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
