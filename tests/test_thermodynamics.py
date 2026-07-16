import pytest

from app.db.models import CoolingType
from app.services.thermodynamics import (
    calculate_evaporation_rate_lph,
    calculate_dynamic_wue,
    calculate_latent_heat_of_vaporization_kj_per_kg,
    calculate_theoretical_evaporation_lph_per_kw,
    calculate_water_consumption_lph,
    calculate_wet_bulb_temperature_c,
)
from app.services.risk import calculate_water_stress_beta
from app.services.phase2_model import estimate_realtime_water_metrics
from app.services.state_store import TelemetrySnapshot


@pytest.mark.parametrize(
    ("dry_bulb", "humidity", "expected"),
    [
        (30.0, 50.0, 22.3),
        (25.0, 70.0, 20.9),
        (35.0, 40.0, 24.6),
    ],
)
def test_stull_wet_bulb_baselines(dry_bulb: float, humidity: float, expected: float) -> None:
    result = calculate_wet_bulb_temperature_c(dry_bulb, humidity)
    assert result == pytest.approx(expected, abs=0.55)


def test_stull_falls_back_to_dry_bulb_when_air_is_too_dry() -> None:
    assert calculate_wet_bulb_temperature_c(40.0, 4.0) == pytest.approx(40.0)


def test_temperate_free_cooling_case_preserves_base_wue() -> None:
    wet_bulb = calculate_wet_bulb_temperature_c(14.0, 60.0)
    modifier = calculate_dynamic_wue(1.8, wet_bulb, CoolingType.DIRECT_EVAPORATIVE) / 1.8

    assert wet_bulb == pytest.approx(10.51, abs=0.55)
    assert modifier == pytest.approx(1.0, abs=1e-6)


def test_desert_case_matches_specified_dynamic_wue_modifier() -> None:
    wet_bulb = calculate_wet_bulb_temperature_c(40.0, 15.0)
    modifier = calculate_dynamic_wue(1.8, wet_bulb, CoolingType.DIRECT_EVAPORATIVE) / 1.8

    assert wet_bulb == pytest.approx(21.09, abs=0.5)
    assert modifier == pytest.approx(1.61, abs=0.06)


def test_dynamic_wue_uses_cooling_sensitivity() -> None:
    wet_bulb = 24.8
    direct = calculate_dynamic_wue(1.8, wet_bulb, CoolingType.DIRECT_EVAPORATIVE)
    closed = calculate_dynamic_wue(1.8, wet_bulb, CoolingType.CLOSED_LOOP)

    assert direct == pytest.approx(3.564, abs=0.001)
    assert closed == pytest.approx(1.9176, abs=0.001)
    assert direct > closed


def test_water_consumption_uses_mw_to_kw_conversion() -> None:
    result = calculate_water_consumption_lph(50.0, 2.97)
    assert result == pytest.approx(148500.0)


def test_latent_heat_and_theoretical_evaporation_match_spec() -> None:
    latent_heat = calculate_latent_heat_of_vaporization_kj_per_kg(20.0)
    lph_per_kw = calculate_theoretical_evaporation_lph_per_kw(20.0)

    assert latent_heat == pytest.approx(2453.78, abs=0.05)
    assert lph_per_kw == pytest.approx(1.47, abs=0.02)


def test_evaporation_rate_scales_with_heat_rejection() -> None:
    assert calculate_evaporation_rate_lph(1.0, 20.0) == pytest.approx(1.47, abs=0.02)
    assert calculate_evaporation_rate_lph(1000.0, 20.0) == pytest.approx(1467.0, abs=8.0)


def test_water_stress_beta_is_nonlinear() -> None:
    assert calculate_water_stress_beta(1.2) == pytest.approx(2.31, abs=0.03)
    assert calculate_water_stress_beta(4.5) == pytest.approx(10.55, abs=0.05)


def test_true_green_index_captures_pue_wue_tradeoff() -> None:
    snapshot = TelemetrySnapshot(
        region_key="aws:us-east-1",
        timestamp="2026-07-15T00:00:00Z",
        dry_bulb_temp_c=31.0,
        relative_humidity_pct=62.0,
        grid_load_factor=0.7,
        carbon_intensity_g_per_kwh=390.0,
        latency_factor=0.55,
        jitter_ms=10.0,
        source="test",
    )
    metrics = estimate_realtime_water_metrics(
        max_capacity_mw=120.0,
        pue=1.21,
        base_wue=1.8,
        cooling_type=CoolingType.DIRECT_EVAPORATIVE,
        water_stress_score=2.2,
        snapshot=snapshot,
    )
    assert float(metrics["stress_adjusted_wue"]) > float(metrics["instant_wue"])
    assert float(metrics["true_green_index"]) == pytest.approx(
        float(metrics["stress_adjusted_wue"]) * 1.21,
        rel=1e-6,
    )
    assert float(metrics["beta_risk"]) == pytest.approx(1.0 + 2.2**1.5, rel=1e-6)
