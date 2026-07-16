from app.core.config import settings
from app.db.models import CoolingType
from app.services.risk import calculate_water_stress_beta, classify_water_stress
from app.services.telemetry import TelemetrySnapshot
from app.services.thermodynamics import (
    calculate_dynamic_wue,
    calculate_water_consumption_lph,
    calculate_wet_bulb_temperature_c,
)


def estimate_dynamic_it_load_mw(max_capacity_mw: float, snapshot: TelemetrySnapshot) -> float:
    normalized_carbon = min(snapshot.carbon_intensity_g_per_kwh / 600.0, 1.0)
    utilization = (
        settings.load_weight_grid * snapshot.grid_load_factor
        + settings.load_weight_latency * snapshot.latency_factor
        + settings.load_weight_carbon * normalized_carbon
    )
    bounded_utilization = min(max(utilization, 0.05), 1.0)
    return max_capacity_mw * bounded_utilization


def estimate_realtime_water_metrics(
    max_capacity_mw: float,
    pue: float,
    base_wue: float,
    cooling_type: CoolingType,
    water_stress_score: float | None,
    snapshot: TelemetrySnapshot,
) -> dict[str, float | str]:
    wet_bulb_temp_c = calculate_wet_bulb_temperature_c(
        snapshot.dry_bulb_temp_c,
        snapshot.relative_humidity_pct,
    )
    dynamic_load_mw = estimate_dynamic_it_load_mw(max_capacity_mw, snapshot)
    instant_wue = calculate_dynamic_wue(base_wue, wet_bulb_temp_c, cooling_type)
    water_lph = calculate_water_consumption_lph(dynamic_load_mw, instant_wue)
    water_stress_tier, _ = classify_water_stress(water_stress_score)
    beta_risk = calculate_water_stress_beta(water_stress_score)
    weighted_impact = water_lph * beta_risk
    stress_adjusted_wue = instant_wue * beta_risk
    true_green_index = pue * stress_adjusted_wue

    return {
        "wet_bulb_temp_c": wet_bulb_temp_c,
        "estimated_it_load_mw": dynamic_load_mw,
        "instant_wue": instant_wue,
        "water_lph": water_lph,
        "weighted_impact": weighted_impact,
        "stress_adjusted_wue": stress_adjusted_wue,
        "true_green_index": true_green_index,
        "water_stress_tier": water_stress_tier,
        "beta_risk": beta_risk,
    }


def project_route_metrics(
    compute_demand_mwh: float,
    job_duration_hours: float,
    base_wue: float,
    cooling_type: CoolingType,
    water_stress_score: float | None,
    snapshot: TelemetrySnapshot,
) -> dict[str, float | str]:
    wet_bulb_temp_c = calculate_wet_bulb_temperature_c(
        snapshot.dry_bulb_temp_c,
        snapshot.relative_humidity_pct,
    )
    instant_wue = calculate_dynamic_wue(base_wue, wet_bulb_temp_c, cooling_type)
    projected_water_liters = compute_demand_mwh * 1000.0 * instant_wue
    projected_carbon_g = compute_demand_mwh * 1000.0 * snapshot.carbon_intensity_g_per_kwh
    water_stress_tier, _ = classify_water_stress(water_stress_score)
    beta_risk = calculate_water_stress_beta(water_stress_score)
    adjusted_impact = projected_water_liters * beta_risk

    return {
        "wet_bulb_temp_c": wet_bulb_temp_c,
        "projected_water_liters": projected_water_liters,
        "projected_carbon_g": projected_carbon_g,
        "water_stress_adjusted_impact_score": adjusted_impact,
        "water_stress_tier": water_stress_tier,
        "beta_risk": beta_risk,
        "average_mw": compute_demand_mwh / job_duration_hours,
    }
