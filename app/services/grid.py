from app.core.config import settings
from app.services.baselines import SEASONAL_BASELINES


class GridServiceError(RuntimeError):
    pass


async def fetch_grid_snapshot(grid_zone_id: str, region_slug: str) -> dict[str, float]:
    baseline = SEASONAL_BASELINES.get(region_slug)
    if baseline is None:
        raise GridServiceError(f"No grid baseline configured for {region_slug}")

    return {
        "grid_zone_id": grid_zone_id,
        "grid_load_factor": baseline["grid_load_factor"],
        "carbon_intensity_g_per_kwh": baseline["carbon_intensity_g_per_kwh"],
        "source": "seasonal-baseline" if settings.electricity_maps_api_key is None else "cached-grid",
    }
