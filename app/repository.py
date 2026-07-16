from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from app.db.models import DataCenter
from app.db.seeds import SEED_DATACENTERS
from app.db.session import SessionLocal


def _serialize_datacenter(model: DataCenter) -> dict[str, Any]:
    return {
        "id": model.id,
        "name": getattr(model, "name", None) or getattr(model, "facility_name", None) or model.region_slug,
        "facility_name": getattr(model, "facility_name", None) or getattr(model, "name", None) or model.region_slug,
        "provider": model.provider,
        "region_slug": model.region_slug,
        "latitude": model.latitude,
        "longitude": model.longitude,
        "max_it_capacity_mw": model.max_it_capacity_mw,
        "pue": model.pue,
        "cooling_type": model.cooling_type,
        "cooling_profile": model.cooling_type.value,
        "base_wue": model.base_wue,
        "grid_zone_id": model.grid_zone_id,
        "water_stress_score": model.water_stress_score,
        "wri_water_stress_score": model.water_stress_score,
        "ping_target_ip": model.ping_target_ip,
    }


async def _list_regions_from_db() -> list[dict[str, Any]]:
    async with SessionLocal() as session:
        result = await session.execute(select(DataCenter).order_by(DataCenter.provider, DataCenter.region_slug))
        return [_serialize_datacenter(item) for item in result.scalars().all()]


async def _get_region_from_db(provider: str, region_slug: str) -> dict[str, Any] | None:
    async with SessionLocal() as session:
        result = await session.execute(
            select(DataCenter).where(
                DataCenter.provider.ilike(provider.strip()),
                DataCenter.region_slug.ilike(region_slug.strip()),
            )
        )
        match = result.scalar_one_or_none()
        return _serialize_datacenter(match) if match is not None else None


async def list_regions() -> Sequence[dict]:
    try:
        regions = await _list_regions_from_db()
        if regions:
            return regions
    except Exception:
        pass
    return SEED_DATACENTERS


async def get_region(provider: str, region_slug: str) -> dict | None:
    try:
        match = await _get_region_from_db(provider, region_slug)
        if match is not None:
            return match
    except Exception:
        pass

    provider_norm = provider.strip().lower()
    region_norm = region_slug.strip().lower()
    for datacenter in SEED_DATACENTERS:
        if datacenter["provider"].lower() == provider_norm and datacenter["region_slug"].lower() == region_norm:
            return datacenter
    return None
