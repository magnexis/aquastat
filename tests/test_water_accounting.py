import pytest

from app.services.water_accounting import (
    aggregate_periods_liters,
    calculate_change_in_storage_liters,
    calculate_consumptive_use_liters,
    calculate_cooling_tower_blowdown_liters,
    calculate_cooling_tower_makeup_liters,
    classify_water_figure,
    cubic_meters_to_liters,
    gallons_to_liters,
    liters_to_cubic_meters,
    liters_to_gallons,
)


def test_unit_round_trips_preserve_value_within_tolerance() -> None:
    liters = 12345.67
    assert gallons_to_liters(liters_to_gallons(liters)) == pytest.approx(liters, rel=1e-9)
    assert cubic_meters_to_liters(liters_to_cubic_meters(liters)) == pytest.approx(liters, rel=1e-9)


def test_consumptive_use_follows_documented_balance() -> None:
    consumptive_use = calculate_consumptive_use_liters(
        withdrawal_liters=1000.0,
        return_flow_liters=300.0,
        storage_change_liters=50.0,
    )
    assert consumptive_use == pytest.approx(650.0)


def test_negative_consumptive_use_is_rejected() -> None:
    with pytest.raises(ValueError):
        calculate_consumptive_use_liters(100.0, 120.0, 0.0)


def test_cooling_tower_makeup_balance_matches_formula() -> None:
    balance = calculate_cooling_tower_makeup_liters(
        evaporation_liters=1000.0,
        drift_liters=30.0,
        blowdown_liters=220.0,
        leakage_liters=10.0,
        storage_change_liters=5.0,
    )
    assert balance.makeup_liters == pytest.approx(1265.0)


def test_increasing_evaporation_cannot_reduce_blowdown_when_cycles_fixed() -> None:
    lower = calculate_cooling_tower_blowdown_liters(800.0, cycles_of_concentration=5.0, drift_liters=10.0)
    higher = calculate_cooling_tower_blowdown_liters(1000.0, cycles_of_concentration=5.0, drift_liters=10.0)
    assert higher >= lower


def test_aggregation_equals_sum_of_subperiods() -> None:
    periods = [100.0, 200.0, 50.0, 25.0]
    assert aggregate_periods_liters(periods) == pytest.approx(sum(periods))
    assert calculate_change_in_storage_liters(500.0, 375.0) == pytest.approx(125.0)


def test_water_figure_classification_does_not_confuse_projection_and_actual() -> None:
    assert classify_water_figure(evidence_class="Level A", is_measured=True) == "metered-verified"
    assert classify_water_figure(evidence_class="Level B", is_permitted_maximum=True) == "official-permitted-maximum"
    assert classify_water_figure(evidence_class="Level D") == "derived"
    assert classify_water_figure(evidence_class="Level E") == "modeled-estimate"
