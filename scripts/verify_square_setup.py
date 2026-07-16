from __future__ import annotations

import json
from pathlib import Path
import sys

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings


def _fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def _mask(value: str | None, *, keep: int = 4) -> str:
    if not value:
        return "<missing>"
    if len(value) <= keep * 2:
        return "*" * len(value)
    return f"{value[:keep]}...{value[-keep:]}"


async def main() -> int:
    required = {
        "AQUASTAT_SQUARE_ACCESS_TOKEN": settings.square_access_token,
        "AQUASTAT_SQUARE_LOCATION_ID": settings.square_location_id,
        "AQUASTAT_SQUARE_WEBHOOK_NOTIFICATION_URL": settings.square_webhook_notification_url,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        return _fail(f"Missing Square configuration: {', '.join(missing)}")

    base_url = (
        "https://connect.squareupsandbox.com"
        if settings.square_environment == "sandbox"
        else "https://connect.squareup.com"
    )
    headers = {
        "Authorization": f"Bearer {settings.square_access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Square-Version": settings.square_api_version,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        locations_response = await client.get(f"{base_url}/v2/locations", headers=headers)
        if locations_response.status_code != 200:
            return _fail(
                "Square location lookup failed: "
                f"{locations_response.status_code} {locations_response.text}"
            )
        payload = locations_response.json()
        locations = payload.get("locations", [])
        selected = next(
            (location for location in locations if location.get("id") == settings.square_location_id),
            None,
        )
        if selected is None:
            known = ", ".join(location.get("id", "<unknown>") for location in locations) or "<none>"
            return _fail(
                "Configured AQUASTAT_SQUARE_LOCATION_ID was not returned by Square. "
                f"Configured={settings.square_location_id!r}, available={known}"
            )

    result = {
        "status": "ok",
        "environment": settings.square_environment,
        "applicationIdConfigured": bool(settings.square_application_id),
        "publicApplicationIdConfigured": bool(settings.public_square_application_id),
        "accessTokenMasked": _mask(settings.square_access_token),
        "locationId": settings.square_location_id,
        "locationName": selected.get("name"),
        "webhookNotificationUrl": settings.square_webhook_notification_url,
        "webhookSignatureConfigured": bool(settings.square_webhook_signature_key),
        "billingEnabled": settings.billing_enabled,
        "cashAppPayEnabled": settings.cash_app_pay_enabled,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(__import__("asyncio").run(main()))
