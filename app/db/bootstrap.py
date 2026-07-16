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
