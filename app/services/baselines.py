SEASONAL_BASELINES: dict[str, dict[str, float]] = {
    "us-east-1": {
        "dry_bulb_temp_c": 29.0,
        "relative_humidity_pct": 68.0,
        "grid_load_factor": 0.71,
        "carbon_intensity_g_per_kwh": 390.0,
        "latency_factor": 0.58,
        "jitter_ms": 11.0,
    },
    "eu-west-1": {
        "dry_bulb_temp_c": 18.0,
        "relative_humidity_pct": 72.0,
        "grid_load_factor": 0.54,
        "carbon_intensity_g_per_kwh": 180.0,
        "latency_factor": 0.36,
        "jitter_ms": 6.0,
    },
    "eu-central-1": {
        "dry_bulb_temp_c": 22.0,
        "relative_humidity_pct": 63.0,
        "grid_load_factor": 0.62,
        "carbon_intensity_g_per_kwh": 290.0,
        "latency_factor": 0.48,
        "jitter_ms": 8.0,
    },
    "asia-southeast1": {
        "dry_bulb_temp_c": 31.0,
        "relative_humidity_pct": 79.0,
        "grid_load_factor": 0.76,
        "carbon_intensity_g_per_kwh": 470.0,
        "latency_factor": 0.61,
        "jitter_ms": 14.0,
    },
    "us-west-2": {
        "dry_bulb_temp_c": 24.0,
        "relative_humidity_pct": 49.0,
        "grid_load_factor": 0.57,
        "carbon_intensity_g_per_kwh": 305.0,
        "latency_factor": 0.42,
        "jitter_ms": 7.0,
    },
}


WATER_STRESS_MULTIPLIERS: list[tuple[float, str, float]] = [
    (1.0, "Low", 1.0),
    (2.0, "Low-Medium", 1.5),
    (3.0, "Medium-High", 2.5),
    (4.0, "High", 3.5),
    (5.0, "Extremely High", 5.0),
]
