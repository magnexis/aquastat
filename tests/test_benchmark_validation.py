import json
from pathlib import Path

import pytest

from app.services.water_accounting import (
    calculate_consumptive_use_liters,
    calculate_cooling_tower_blowdown_liters,
)


@pytest.mark.parametrize(
    "fixture_path",
    [
        Path("tests/fixtures/benchmarks/metered_cooling_tower_case.json"),
        Path("tests/fixtures/benchmarks/cycles_of_concentration_case.json"),
    ],
)
def test_scientific_benchmark_fixtures_remain_within_tolerance(fixture_path: Path) -> None:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

    if fixture["name"] == "metered_cooling_tower_case":
        result = calculate_consumptive_use_liters(
            withdrawal_liters=fixture["withdrawal_liters"],
            return_flow_liters=fixture["return_flow_liters"],
            storage_change_liters=fixture["storage_change_liters"],
        )
        assert result == pytest.approx(fixture["expected_consumptive_use_liters"], abs=fixture["tolerance_liters"])

    if fixture["name"] == "cycles_of_concentration_case":
        result = calculate_cooling_tower_blowdown_liters(
            evaporation_liters=fixture["evaporation_liters"],
            cycles_of_concentration=fixture["cycles_of_concentration"],
            drift_liters=fixture["drift_liters"],
        )
        assert result == pytest.approx(fixture["expected_blowdown_liters"], abs=fixture["tolerance_liters"])
