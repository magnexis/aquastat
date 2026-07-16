import asyncio
import logging

from app.core.config import settings
from app.services.ingestion import ingest_once


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("aquastat.ingest")


async def run_forever() -> None:
    while True:
        count = await ingest_once()
        logger.info("refreshed telemetry for %s datacenters", count)
        await asyncio.sleep(settings.telemetry_refresh_interval_seconds)


if __name__ == "__main__":
    asyncio.run(run_forever())
