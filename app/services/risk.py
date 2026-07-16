from app.services.baselines import WATER_STRESS_MULTIPLIERS


def classify_water_stress(score: float | None) -> tuple[str, float]:
    bounded = min(max(score or 1.0, 0.0), 5.0)
    for upper_bound, tier, multiplier in WATER_STRESS_MULTIPLIERS:
        if bounded <= upper_bound:
            return tier, multiplier
    return "Extremely High", 5.0


def calculate_water_stress_beta(score: float | None) -> float:
    bounded = min(max(score or 0.0, 0.0), 5.0)
    return 1.0 + bounded**1.5
