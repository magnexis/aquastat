import time

try:
    from cachetools import TTLCache
except ModuleNotFoundError:  # pragma: no cover
    class TTLCache(dict):
        def __init__(self, maxsize: int, ttl: int) -> None:
            super().__init__()
            self.maxsize = maxsize
            self.ttl = ttl
            self._timestamps: dict[object, float] = {}

        def __setitem__(self, key: object, value: object) -> None:
            if len(self) >= self.maxsize and key not in self:
                oldest_key = min(self._timestamps, key=self._timestamps.get)
                super().pop(oldest_key, None)
                self._timestamps.pop(oldest_key, None)
            super().__setitem__(key, value)
            self._timestamps[key] = time.monotonic()

        def get(self, key: object, default: object = None) -> object:
            timestamp = self._timestamps.get(key)
            if timestamp is None:
                return default
            if (time.monotonic() - timestamp) > self.ttl:
                super().pop(key, None)
                self._timestamps.pop(key, None)
                return default
            return super().get(key, default)

from app.core.config import settings


weather_cache = TTLCache(maxsize=settings.weather_cache_maxsize, ttl=settings.weather_cache_ttl_seconds)


def make_weather_cache_key(latitude: float, longitude: float) -> str:
    lat_bucket = round(latitude, 2)
    lon_bucket = round(longitude, 2)
    return f"{lat_bucket}:{lon_bucket}"
