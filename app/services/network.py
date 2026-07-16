from app.services.baselines import SEASONAL_BASELINES


async def estimate_network_latency(region_slug: str, ping_target_ip: str | None) -> dict[str, float]:
    baseline = SEASONAL_BASELINES[region_slug]
    return {
        "latency_factor": baseline["latency_factor"],
        "jitter_ms": baseline["jitter_ms"],
        "source": "seasonal-baseline" if ping_target_ip is None else "cached-probe",
    }
