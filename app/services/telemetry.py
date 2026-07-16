from datetime import UTC, datetime

from app.repository import list_regions
from app.services.baselines import SEASONAL_BASELINES
from app.services.grid import fetch_grid_snapshot
from app.services.network import estimate_network_latency
from app.services.state_store import TelemetrySnapshot, state_store
from app.services.weather import WeatherServiceError, fetch_current_weather


def make_region_key(provider: str, region_slug: str) -> str:
    return f"{provider.lower()}:{region_slug.lower()}"


async def build_snapshot(datacenter: dict) -> TelemetrySnapshot:
    region_slug = datacenter["region_slug"]
    region_key = make_region_key(datacenter["provider"], region_slug)

    try:
        weather = await fetch_current_weather(datacenter["latitude"], datacenter["longitude"])
        weather_source = "live-weather"
    except WeatherServiceError:
        baseline = SEASONAL_BASELINES[region_slug]
        weather = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "dry_bulb_temp_c": baseline["dry_bulb_temp_c"],
            "relative_humidity_pct": baseline["relative_humidity_pct"],
            "source": "seasonal-baseline",
            "quality": "estimated",
        }
        weather_source = "seasonal-baseline"

    grid = await fetch_grid_snapshot(datacenter.get("grid_zone_id") or "", region_slug)
    network = await estimate_network_latency(region_slug, datacenter.get("ping_target_ip"))

    return TelemetrySnapshot(
        region_key=region_key,
        timestamp=str(weather["timestamp"]),
        dry_bulb_temp_c=float(weather["dry_bulb_temp_c"]),
        relative_humidity_pct=float(weather["relative_humidity_pct"]),
        grid_load_factor=float(grid["grid_load_factor"]),
        carbon_intensity_g_per_kwh=float(grid["carbon_intensity_g_per_kwh"]),
        latency_factor=float(network["latency_factor"]),
        jitter_ms=float(network["jitter_ms"]),
        source=",".join([weather_source, str(grid["source"]), str(network["source"])]),
    )


async def refresh_all_telemetry() -> None:
    regions = await list_regions()
    for datacenter in regions:
        snapshot = await build_snapshot(datacenter)
        await state_store.set_snapshot(snapshot)


async def get_cached_or_baseline_snapshot(datacenter: dict) -> TelemetrySnapshot:
    region_key = make_region_key(datacenter["provider"], datacenter["region_slug"])
    cached = await state_store.get_snapshot(region_key)
    if cached is not None:
        return cached
    baseline = SEASONAL_BASELINES[datacenter["region_slug"]]
    snapshot = TelemetrySnapshot(
        region_key=region_key,
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        dry_bulb_temp_c=baseline["dry_bulb_temp_c"],
        relative_humidity_pct=baseline["relative_humidity_pct"],
        grid_load_factor=baseline["grid_load_factor"],
        carbon_intensity_g_per_kwh=baseline["carbon_intensity_g_per_kwh"],
        latency_factor=baseline["latency_factor"],
        jitter_ms=baseline["jitter_ms"],
        source="seasonal-baseline",
    )
    await state_store.set_snapshot(snapshot)
    return snapshot
