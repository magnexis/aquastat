from __future__ import annotations

from dataclasses import dataclass


LITERS_PER_GALLON = 3.785411784
GALLONS_PER_LITER = 1.0 / LITERS_PER_GALLON
LITERS_PER_CUBIC_METER = 1000.0
HOURS_PER_DAY = 24.0
HOURS_PER_YEAR = 24.0 * 365.0


@dataclass(frozen=True)
class WaterBalance:
    total_inflow_liters: float
    total_outflow_liters: float
    storage_change_liters: float


@dataclass(frozen=True)
class CoolingTowerBalance:
    evaporation_liters: float
    drift_liters: float
    blowdown_liters: float
    leakage_liters: float
    storage_change_liters: float
    makeup_liters: float


def liters_to_gallons(liters: float) -> float:
    return liters * GALLONS_PER_LITER


def gallons_to_liters(gallons: float) -> float:
    return gallons * LITERS_PER_GALLON


def liters_to_cubic_meters(liters: float) -> float:
    return liters / LITERS_PER_CUBIC_METER


def cubic_meters_to_liters(cubic_meters: float) -> float:
    return cubic_meters * LITERS_PER_CUBIC_METER


def calculate_change_in_storage_liters(total_inflow_liters: float, total_outflow_liters: float) -> float:
    return total_inflow_liters - total_outflow_liters


def calculate_consumptive_use_liters(
    withdrawal_liters: float,
    return_flow_liters: float,
    storage_change_liters: float = 0.0,
) -> float:
    consumptive_use = withdrawal_liters - return_flow_liters - storage_change_liters
    if consumptive_use < 0:
        raise ValueError("Consumptive use cannot be negative under the documented balance.")
    return consumptive_use


def calculate_cooling_tower_blowdown_liters(
    evaporation_liters: float,
    cycles_of_concentration: float,
    drift_liters: float = 0.0,
) -> float:
    if cycles_of_concentration <= 1.0:
        raise ValueError("Cycles of concentration must be greater than 1.0.")
    if evaporation_liters < 0.0 or drift_liters < 0.0:
        raise ValueError("Evaporation and drift must be non-negative.")
    return max(0.0, (evaporation_liters / (cycles_of_concentration - 1.0)) - drift_liters)


def calculate_cooling_tower_makeup_liters(
    evaporation_liters: float,
    drift_liters: float,
    blowdown_liters: float,
    leakage_liters: float = 0.0,
    storage_change_liters: float = 0.0,
) -> CoolingTowerBalance:
    for value in (evaporation_liters, drift_liters, blowdown_liters, leakage_liters):
        if value < 0.0:
            raise ValueError("Cooling-tower losses must be non-negative.")
    makeup_liters = evaporation_liters + drift_liters + blowdown_liters + leakage_liters + storage_change_liters
    if makeup_liters < 0.0:
        raise ValueError("Cooling-tower makeup cannot be negative.")
    return CoolingTowerBalance(
        evaporation_liters=evaporation_liters,
        drift_liters=drift_liters,
        blowdown_liters=blowdown_liters,
        leakage_liters=leakage_liters,
        storage_change_liters=storage_change_liters,
        makeup_liters=makeup_liters,
    )


def aggregate_periods_liters(period_values_liters: list[float]) -> float:
    if any(value < 0.0 for value in period_values_liters):
        raise ValueError("Aggregated water volumes must be non-negative.")
    return sum(period_values_liters)


def classify_water_figure(
    *,
    evidence_class: str,
    is_projected: bool = False,
    is_permitted_maximum: bool = False,
    is_measured: bool = False,
) -> str:
    if evidence_class == "Level A":
        return "metered-verified" if is_measured else "verified"
    if evidence_class == "Level B":
        if is_permitted_maximum:
            return "official-permitted-maximum"
        if is_projected:
            return "official-projected"
        return "official-reported"
    if evidence_class == "Level C":
        return "corroborated-observational"
    if evidence_class == "Level D":
        return "derived"
    if evidence_class == "Level E":
        return "modeled-estimate"
    if evidence_class == "Level F":
        return "unverified-claim"
    return "unknown"
