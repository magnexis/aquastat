from datetime import datetime

import httpx

from app.metrics import record_cache_result
from app.core.config import settings
from app.services.circuit_breaker import circuit_breaker
from app.services.cache import make_weather_cache_key, weather_cache


class WeatherServiceError(RuntimeError):
    pass


async def fetch_current_weather(latitude: float, longitude: float) -> dict[str, float | str]:
    cache_key = make_weather_cache_key(latitude, longitude)
    cached = weather_cache.get(cache_key)
    if cached is not None:
        record_cache_result("weather", True)
        cached["source"] = "cache"
        cached["quality"] = "cached"
        return cached
    record_cache_result("weather", False)
    if circuit_breaker.is_open("open-meteo"):
        raise WeatherServiceError("Weather circuit breaker open")

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(settings.open_meteo_base_url, params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            circuit_breaker.record_failure("open-meteo")
            raise WeatherServiceError("Unable to fetch weather data") from exc

    payload = response.json()
    current = payload.get("current") or {}
    if "temperature_2m" not in current or "relative_humidity_2m" not in current:
        raise WeatherServiceError("Weather payload missing required fields")

    snapshot = {
        "timestamp": current.get("time") or datetime.utcnow().isoformat() + "Z",
        "dry_bulb_temp_c": float(current["temperature_2m"]),
        "relative_humidity_pct": float(current["relative_humidity_2m"]),
        "source": "open-meteo",
        "quality": "observed",
    }
    circuit_breaker.record_success("open-meteo")
    weather_cache[cache_key] = snapshot
    return snapshot
