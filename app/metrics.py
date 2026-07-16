from collections.abc import Callable
from time import perf_counter

from fastapi import FastAPI, Request, Response

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
except ModuleNotFoundError:  # pragma: no cover
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

    class _NoopMetric:
        def labels(self, **_: str) -> "_NoopMetric":
            return self

        def inc(self, *_: float) -> None:
            return None

        def observe(self, *_: float) -> None:
            return None

    def Counter(*_: object, **__: object) -> _NoopMetric:
        return _NoopMetric()

    def Histogram(*_: object, **__: object) -> _NoopMetric:
        return _NoopMetric()

    def generate_latest() -> bytes:
        return b""


REQUEST_COUNT = Counter(
    "aquastat_api_requests_total",
    "Total number of requests served by the API",
    ["method", "path", "provider", "region", "status_code"],
)

CALCULATION_LATENCY = Histogram(
    "aquastat_calculation_seconds",
    "Time spent serving AquaStat HTTP requests",
    ["method", "path"],
    buckets=[0.001, 0.005, 0.010, 0.050, 0.100, 0.500, 1.0],
)

CACHE_HITS = Counter(
    "aquastat_cache_hits_total",
    "Total count of cache hits and misses",
    ["cache_name", "status"],
)


def record_cache_result(cache_name: str, hit: bool) -> None:
    CACHE_HITS.labels(cache_name=cache_name, status="hit" if hit else "miss").inc()


def instrument_app(app: FastAPI) -> None:
    @app.middleware("http")
    async def record_metrics(request: Request, call_next: Callable) -> Response:
        provider = request.query_params.get("provider", "n/a")
        region = request.query_params.get("region", "n/a")
        path = request.url.path
        method = request.method
        started = perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration = perf_counter() - started
            REQUEST_COUNT.labels(
                method=method,
                path=path,
                provider=provider,
                region=region,
                status_code=str(status_code),
            ).inc()
            CALCULATION_LATENCY.labels(method=method, path=path).observe(duration)

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
