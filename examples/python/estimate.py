import os

import httpx


def main() -> None:
    api_key = os.environ["AQUASTAT_API_KEY"]
    base_url = os.environ.get("AQUASTAT_BASE_URL", "http://localhost:8080")
    response = httpx.get(
        f"{base_url}/api/v1/estimate",
        params={"provider": "aws", "region": "us-east-1", "load_mw": 2.5},
        headers={"X-API-Key": api_key},
        timeout=10.0,
    )
    response.raise_for_status()
    print(response.json())


if __name__ == "__main__":
    main()
