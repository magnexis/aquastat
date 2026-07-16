import math

from app.db.models import CoolingType


COOLING_MULTIPLIERS: dict[CoolingType, float] = {
    CoolingType.DIRECT_EVAPORATIVE: 1.5,
    CoolingType.ADIABATIC_HYBRID: 0.8,
    CoolingType.CLOSED_LOOP: 0.1,
}

WET_BULB_MIN_RELATIVE_HUMIDITY_PCT = 5.0
WET_BULB_MAX_RELATIVE_HUMIDITY_PCT = 99.0
WET_BULB_MIN_DRY_BULB_C = -20.0
WET_BULB_MAX_DRY_BULB_C = 50.0
WET_BULB_THRESHOLD_C = 15.0
WET_BULB_SPAN_C = 15.0
LITERS_PER_CUBIC_METER = 1000.0
STANDARD_ATMOSPHERIC_PRESSURE_HPA = 1013.25


def calculate_latent_heat_of_vaporization_kj_per_kg(water_temp_c: float) -> float:
    return 2501.0 - 2.361 * water_temp_c


def calculate_theoretical_evaporation_lph_per_kw(reference_temp_c: float = 20.0) -> float:
    latent_heat = calculate_latent_heat_of_vaporization_kj_per_kg(reference_temp_c)
    kg_per_second = 1.0 / latent_heat
    return kg_per_second * 3600.0


def _saturation_vapor_pressure_hpa(temp_c: float) -> float:
    return 6.112 * math.exp((17.67 * temp_c) / (temp_c + 243.5))


def _stull_wet_bulb_estimate_c(dry_bulb_temp_c: float, relative_humidity_pct: float) -> float:
    rh = relative_humidity_pct
    t = dry_bulb_temp_c
    return (
        t * math.atan(0.151977 * math.sqrt(rh + 8.313659))
        + math.atan(t + rh)
        - math.atan(rh - 1.676331)
        + 0.00391838 * math.sqrt(rh**3) * math.atan(0.023101 * rh)
        - 4.686035
    )


def calculate_wet_bulb_temperature_c(dry_bulb_temp_c: float, relative_humidity_pct: float) -> float:
    if relative_humidity_pct < WET_BULB_MIN_RELATIVE_HUMIDITY_PCT:
        return dry_bulb_temp_c

    rh = min(max(relative_humidity_pct, WET_BULB_MIN_RELATIVE_HUMIDITY_PCT), WET_BULB_MAX_RELATIVE_HUMIDITY_PCT)
    t = min(max(dry_bulb_temp_c, WET_BULB_MIN_DRY_BULB_C), WET_BULB_MAX_DRY_BULB_C)
    vapor_pressure = (rh / 100.0) * _saturation_vapor_pressure_hpa(t)
    stull_guess = _stull_wet_bulb_estimate_c(t, rh)

    low = WET_BULB_MIN_DRY_BULB_C
    high = t
    guess = min(max(stull_guess, low), high)

    for _ in range(40):
        psychrometric_constant = 0.00066 * (1.0 + 0.00115 * guess) * STANDARD_ATMOSPHERIC_PRESSURE_HPA
        estimated_vapor_pressure = _saturation_vapor_pressure_hpa(guess) - psychrometric_constant * (t - guess)
        if estimated_vapor_pressure > vapor_pressure:
            high = guess
        else:
            low = guess
        guess = (low + high) / 2.0

    return guess


def calculate_dynamic_wue(base_wue: float, wet_bulb_temp_c: float, cooling_type: CoolingType) -> float:
    severity = max(0.0, (wet_bulb_temp_c - WET_BULB_THRESHOLD_C) / WET_BULB_SPAN_C)
    return base_wue * (1.0 + severity * COOLING_MULTIPLIERS[cooling_type])


def calculate_water_consumption_lph(it_load_mw: float, instant_wue: float) -> float:
    return it_load_mw * 1000.0 * instant_wue


def calculate_evaporation_rate_lph(heat_load_kw: float, water_temp_c: float = 20.0) -> float:
    latent_heat = calculate_latent_heat_of_vaporization_kj_per_kg(water_temp_c)
    kg_per_second = heat_load_kw / latent_heat
    return kg_per_second * 3600.0
