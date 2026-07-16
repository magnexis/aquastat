import asyncio
import contextlib

from app.core.config import settings
from app.services.telemetry import refresh_all_telemetry


class TelemetryRefresher:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _run(self) -> None:
        while True:
            await refresh_all_telemetry()
            await asyncio.sleep(settings.telemetry_refresh_interval_seconds)


telemetry_refresher = TelemetryRefresher()
