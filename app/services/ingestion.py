from app.repository import list_regions
from app.services.telemetry import build_snapshot
from app.services.state_store import state_store


async def ingest_once() -> int:
    count = 0
    for datacenter in await list_regions():
        snapshot = await build_snapshot(datacenter)
        await state_store.set_snapshot(snapshot)
        count += 1
    return count
