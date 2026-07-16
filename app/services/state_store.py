from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any

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
from app.metrics import record_cache_result

try:
    from redis.asyncio import Redis
except Exception:  # pragma: no cover
    Redis = None

RedisClient = Any

RATE_LIMIT_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local refill = tonumber(ARGV[3])
local ttl = tonumber(ARGV[4])

local bucket = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(bucket[1])
local ts = tonumber(bucket[2])

if tokens == nil then
  tokens = capacity
  ts = now
end

local elapsed = math.max(0, now - ts)
tokens = math.min(capacity, tokens + (elapsed * refill))
local allowed = 0
if tokens >= 1 then
  tokens = tokens - 1
  allowed = 1
end

redis.call('HMSET', key, 'tokens', tokens, 'ts', now)
redis.call('EXPIRE', key, ttl)
return {allowed, tokens}
"""


@dataclass
class TelemetrySnapshot:
    region_key: str
    timestamp: str
    dry_bulb_temp_c: float
    relative_humidity_pct: float
    grid_load_factor: float
    carbon_intensity_g_per_kwh: float
    latency_factor: float
    jitter_ms: float
    source: str


@dataclass
class RateLimitDecision:
    allowed: bool
    remaining: int
    limit: int
    reset_epoch: int


class StateStore:
    def __init__(self) -> None:
        self._cache = TTLCache(maxsize=512, ttl=settings.state_cache_ttl_seconds)
        self._redis: RedisClient | None = None
        self._lock = asyncio.Lock()
        self._rl_sha: str | None = None
        self._local_buckets: dict[str, tuple[float, float]] = {}

    async def _get_redis(self) -> RedisClient | None:
        if not settings.redis_enabled or Redis is None:
            return None
        if self._redis is None:
            async with self._lock:
                if self._redis is None:
                    self._redis = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        return self._redis

    async def get_snapshot(self, region_key: str) -> TelemetrySnapshot | None:
        snapshot = self._cache.get(region_key)
        if snapshot is not None:
            record_cache_result("telemetry", True)
            return snapshot

        redis_client = await self._get_redis()
        if redis_client is None:
            record_cache_result("telemetry", False)
            return None

        payload = await redis_client.get(f"telemetry:{region_key}")
        if payload is None:
            record_cache_result("telemetry", False)
            return None

        snapshot = TelemetrySnapshot(**json.loads(payload))
        self._cache[region_key] = snapshot
        record_cache_result("telemetry", True)
        return snapshot

    async def set_snapshot(self, snapshot: TelemetrySnapshot) -> None:
        self._cache[snapshot.region_key] = snapshot
        redis_client = await self._get_redis()
        if redis_client is not None:
            await redis_client.setex(
                f"telemetry:{snapshot.region_key}",
                settings.state_cache_ttl_seconds,
                json.dumps(asdict(snapshot)),
            )

    async def list_cached_snapshots(self, region_keys: Iterable[str]) -> list[TelemetrySnapshot]:
        snapshots: list[TelemetrySnapshot] = []
        for region_key in region_keys:
            snapshot = await self.get_snapshot(region_key)
            if snapshot is not None:
                snapshots.append(snapshot)
        return snapshots

    async def _load_rate_limit_script(self, redis_client: RedisClient) -> str:
        if self._rl_sha is None:
            self._rl_sha = await redis_client.script_load(RATE_LIMIT_LUA)
        return self._rl_sha

    async def evaluate_rate_limit(self, subject: str, limit: int, window_seconds: int) -> RateLimitDecision:
        now = int(time.time())
        refill_per_second = limit / max(window_seconds, 1)
        reset_epoch = now + window_seconds
        redis_client = await self._get_redis()

        if redis_client is not None:
            sha = await self._load_rate_limit_script(redis_client)
            key = f"ratelimit:{subject}"
            try:
                allowed, remaining = await redis_client.evalsha(
                    sha,
                    1,
                    key,
                    now,
                    limit,
                    refill_per_second,
                    window_seconds,
                )
            except Exception:
                allowed, remaining = await redis_client.eval(
                    RATE_LIMIT_LUA,
                    1,
                    key,
                    now,
                    limit,
                    refill_per_second,
                    window_seconds,
                )
            return RateLimitDecision(bool(int(allowed)), int(float(remaining)), limit, reset_epoch)

        return self._evaluate_rate_limit_local(subject, limit, window_seconds)

    def _evaluate_rate_limit_local(self, subject: str, limit: int, window_seconds: int) -> RateLimitDecision:
        now = time.monotonic()
        refill_per_second = limit / max(window_seconds, 1)
        tokens, last_time = self._local_buckets.get(subject, (float(limit), now))
        elapsed = max(0.0, now - last_time)
        tokens = min(float(limit), tokens + elapsed * refill_per_second)
        allowed = tokens >= 1.0
        if allowed:
            tokens -= 1.0
        self._local_buckets[subject] = (tokens, now)
        return RateLimitDecision(allowed, int(tokens), limit, int(time.time()) + window_seconds)


state_store = StateStore()
