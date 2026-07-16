from __future__ import annotations

from contextlib import AbstractAsyncContextManager, AbstractContextManager
from dataclasses import dataclass
from time import perf_counter
from typing import Any

import httpx


@dataclass
class WorkloadProfileResult:
    provider: str
    region: str
    estimated_load_mw: float
    elapsed_seconds: float
    estimate: dict[str, Any]


class _ProfileScope(AbstractContextManager):
    def __init__(self, client: "AquaStatClient", provider: str, region: str, est_mw: float) -> None:
        self.client = client
        self.provider = provider
        self.region = region
        self.est_mw = est_mw
        self.started = 0.0
        self.result: WorkloadProfileResult | None = None

    def __enter__(self) -> "_ProfileScope":
        self.started = perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        elapsed = perf_counter() - self.started
        estimate = self.client.check_workload_footprint(self.provider, self.region, self.est_mw)
        self.result = WorkloadProfileResult(self.provider, self.region, self.est_mw, elapsed, estimate)
        return None


class _AsyncProfileScope(AbstractAsyncContextManager):
    def __init__(self, client: "AquaStatClient", provider: str, region: str, est_mw: float) -> None:
        self.client = client
        self.provider = provider
        self.region = region
        self.est_mw = est_mw
        self.started = 0.0
        self.result: WorkloadProfileResult | None = None

    async def __aenter__(self) -> "_AsyncProfileScope":
        self.started = perf_counter()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        elapsed = perf_counter() - self.started
        estimate = await self.client.check_workload_footprint_async(self.provider, self.region, self.est_mw)
        self.result = WorkloadProfileResult(self.provider, self.region, self.est_mw, elapsed, estimate)
        return None


class AquaStatClient:
    def __init__(self, api_key: str | None = None, api_url: str = "https://aquastat-api.onrender.com/api/v1") -> None:
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self._sync = httpx.Client(timeout=10.0, headers=self._default_headers())
        self._async = httpx.AsyncClient(timeout=10.0, headers=self._default_headers())

    def _default_headers(self) -> dict[str, str]:
        headers = {"User-Agent": "aquastat-sdk-python/1.1.2"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def close(self) -> None:
        self._sync.close()

    async def aclose(self) -> None:
        await self._async.aclose()

    def profile_workload(self, provider: str, region: str, est_mw: float) -> _ProfileScope:
        return _ProfileScope(self, provider, region, est_mw)

    def profile_workload_async(self, provider: str, region: str, est_mw: float) -> _AsyncProfileScope:
        return _AsyncProfileScope(self, provider, region, est_mw)

    def check_workload_footprint(self, provider: str, region: str, estimated_load_mw: float) -> dict[str, Any]:
        response = self._sync.get(
            f"{self.api_url}/estimate",
            params={"provider": provider, "region": region, "load_mw": estimated_load_mw},
        )
        response.raise_for_status()
        return response.json()

    async def check_workload_footprint_async(self, provider: str, region: str, estimated_load_mw: float) -> dict[str, Any]:
        response = await self._async.get(
            f"{self.api_url}/estimate",
            params={"provider": provider, "region": region, "load_mw": estimated_load_mw},
        )
        response.raise_for_status()
        return response.json()

    def route_workload(self, job_duration_hours: float, compute_demand_mwh: float, candidate_regions: list[str]) -> dict[str, Any]:
        response = self._sync.post(
            f"{self.api_url}/route-workload",
            json={
                "job_duration_hours": job_duration_hours,
                "compute_demand_mwh": compute_demand_mwh,
                "candidate_regions": candidate_regions,
            },
        )
        response.raise_for_status()
        return response.json()

    async def route_workload_async(
        self, job_duration_hours: float, compute_demand_mwh: float, candidate_regions: list[str]
    ) -> dict[str, Any]:
        response = await self._async.post(
            f"{self.api_url}/route-workload",
            json={
                "job_duration_hours": job_duration_hours,
                "compute_demand_mwh": compute_demand_mwh,
                "candidate_regions": candidate_regions,
            },
        )
        response.raise_for_status()
        return response.json()


def fastapi_dependency(client: AquaStatClient):
    async def _dependency() -> AquaStatClient:
        return client

    return _dependency


def flask_extension(app, client: AquaStatClient) -> None:
    app.extensions["aquastat"] = client


def django_setting() -> str:
    return "AQUASTAT_CLIENT"
