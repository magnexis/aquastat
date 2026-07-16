# AquaStat API

[![CI](https://github.com/magnexis/aquastat/actions/workflows/ci.yml/badge.svg)](https://github.com/magnexis/aquastat/actions/workflows/ci.yml)
[![Docs](https://github.com/magnexis/aquastat/actions/workflows/docs.yml/badge.svg)](https://github.com/magnexis/aquastat/actions/workflows/docs.yml)
[![Release](https://img.shields.io/github/v/release/magnexis/aquastat?display_name=tag)](https://github.com/magnexis/aquastat/releases)
[![License](https://img.shields.io/github/license/magnexis/aquastat)](https://github.com/magnexis/aquastat/blob/main/LICENSE)
[![OpenAPI 3.1](https://img.shields.io/badge/OpenAPI-3.1-0f766e)](https://github.com/magnexis/aquastat/blob/main/openapi/openapi.yaml)

AquaStat is a transparent data-center water intelligence API.

It combines public-style facility records, environmental disclosures, planning-document patterns, utility context, cooling-system metadata, grid characteristics, and estimation models to evaluate the direct and indirect water footprint of data centers.

Every result distinguishes documented, parsed, inferred, and estimated values and includes provenance, confidence, assumptions, and model versions.

AquaStat also distinguishes whether a published water figure is metered, officially reported, corroborated, derived, modeled, unverified, or unknown. It does not collapse permit maxima, projections, derived calculations, and measured values into the same category.

The repository also now includes:

- a lawful public-record request template workflow for facilities
- a typed source-connector registry
- benchmark validation fixtures for water-accounting formulas
- a strict TypeScript desktop foundation in `desktop/`

Limitation:
AquaStat is a research and estimation platform. Facility records may be synthetic, incomplete, conflicting, outdated, or based on public-planning-style documents rather than verified operational measurements. AquaStat results are not regulatory findings or audited disclosures.

Control Center:
Pending Railway deployment

Production API:
Pending Railway deployment

Interactive documentation:
Pending Railway deployment

OpenAPI:
Pending Railway deployment

OpenAPI YAML:
Pending Railway deployment

Health:
Pending Railway deployment

GitHub Pages:
`https://magnexis.github.io/aquastat/`

GitHub Pages OpenAPI:
`https://magnexis.github.io/aquastat/openapi.json`

GitHub Pages OpenAPI YAML:
`https://magnexis.github.io/aquastat/openapi.yaml`

## What Problem It Solves

Cloud infrastructure decisions are usually optimized around latency, cost, and carbon. AquaStat adds water awareness by modeling how weather, cooling design, and regional water stress affect operational water impact.

## Key Capabilities

- Estimate instantaneous water use for supported cloud regions
- Search synthetic Phase 3 facility records with evidence, sources, and history
- Generate facility-based estimates from source-linked registry records
- Use the AquaStat Control Center for overview metrics, calculations, facilities, request diagnostics, and API-key operations
- Model wet-bulb-driven WUE changes
- Rank workload destinations by water and carbon impact
- Expose GeoJSON stress-map outputs
- Parse billing CSVs into water-footprint estimates
- Provide OpenAPI docs, Postman assets, and deployable infrastructure

## Authentication

Protected endpoints accept either:

```http
X-API-Key: aq_live_your_key
```

or:

```http
Authorization: Bearer aq_live_your_key
```

Generate a key locally:

```bash
python scripts/generate_api_key.py
```

Store the resulting hash in:

```env
AQUASTAT_API_KEY_HASHES=generated_hash_here
AQUASTAT_ADMIN_API_KEY_HASHES=generated_admin_hash_here
```

Managed control-center keys support scoped access such as `calculations:read`, `calculations:write`, `facilities:read`, `facilities:write`, and `usage:read`. Environment-level keys configured through `AQUASTAT_API_KEY_HASHES` remain full-access operator keys.

## Quick Start

### cURL

```bash
curl -sS "https://YOUR-SERVICE.up.railway.app/api/v1/estimate?provider=aws&region=us-east-1&load_mw=2.5" \
  -H "X-API-Key: aq_live_your_key"
```

### JavaScript

```js
const response = await fetch(
  "https://YOUR-SERVICE.up.railway.app/api/v1/estimate?provider=aws&region=us-east-1&load_mw=2.5",
  { headers: { "X-API-Key": process.env.AQUASTAT_API_KEY } }
);
console.log(await response.json());
```

### Python

```python
import os
import httpx

response = httpx.get(
    "https://YOUR-SERVICE.up.railway.app/api/v1/estimate",
    params={"provider": "aws", "region": "us-east-1", "load_mw": 2.5},
    headers={"X-API-Key": os.environ["AQUASTAT_API_KEY"]},
    timeout=10.0,
)
print(response.json())
```

## Main Endpoints

- `GET /health`
- `GET /api/v1/status`
- `GET /api/v1/info`
- `GET /api/v1/regions`
- `GET /api/v1/estimate`
- `GET /api/v1/facilities`
- `GET /api/v1/facilities/{facilityId}`
- `POST /api/v1/facilities/{facilityId}/estimate`
- `GET /control-center`
- `GET /health/live`
- `GET /health/ready`
- `GET /version`
- `GET /api/v1/stress-map`
- `GET /api/v1/benchmark`
- `POST /api/v1/route-workload`
- `POST /api/v1/footprint`
- compatibility routes also remain under `/api/v2`

## Rate Limits

- Anonymous: 60 requests/hour
- Developer API key: 10,000 requests/day
- Standard headers: `RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Reset`, `Retry-After`

See [docs/rate-limits.md](/abs/path/C:/Users/matth/OneDrive/Desktop/we%20lit/aquastat/docs/rate-limits.md).

## Control Center

Open the backend-served control center at `/control-center`. It uses AquaStat endpoints directly for:

- overview metrics
- interactive estimate submission
- facility inspection
- request explorer
- model registry inspection
- managed API key actions for operators with an admin API key

## Error Format

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "requestId": "unique-request-id"
  }
}
```

## Local Development

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e .[dev]
python scripts/generate_openapi.py
python scripts/build_docs_site.py
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Run tests:

```bash
pytest
```

## Railway Deployment

- Config: [railway.json](/abs/path/C:/Users/matth/OneDrive/Desktop/we%20lit/aquastat/railway.json)
- Guide: [docs/deployment-railway.md](/abs/path/C:/Users/matth/OneDrive/Desktop/we%20lit/aquastat/docs/deployment-railway.md)

To enable durable control-center state in production, install the normal database dependencies and apply [sql/schema.sql](/abs/path/C:/Users/matth/OneDrive/Desktop/we%20lit/aquastat/sql/schema.sql) before expecting request history, managed keys, and audit events to persist across restarts.

## Docker

```bash
docker build -t aquastat-api .
docker run --rm -p 8080:8080 --env-file .env aquastat-api
```

## Postman and OpenAPI

- Postman collection: [postman/AquaStat-API.postman_collection.json](/abs/path/C:/Users/matth/OneDrive/Desktop/we%20lit/aquastat/postman/AquaStat-API.postman_collection.json)
- OpenAPI source: runtime app schema and generated [openapi/openapi.json](/abs/path/C:/Users/matth/OneDrive/Desktop/we%20lit/aquastat/openapi/openapi.json) and [openapi/openapi.yaml](/abs/path/C:/Users/matth/OneDrive/Desktop/we%20lit/aquastat/openapi/openapi.yaml)

## Examples

See [examples](/abs/path/C:/Users/matth/OneDrive/Desktop/we%20lit/aquastat/examples).

## GitHub Pages

Build the static technical docs artifact locally with:

```bash
python scripts/build_docs_site.py
```

The Pages guide is in [GITHUB_PAGES.md](/abs/path/C:/Users/matth/OneDrive/Desktop/we%20lit/aquastat/GITHUB_PAGES.md).

## Security Reporting

See [SECURITY.md](/abs/path/C:/Users/matth/OneDrive/Desktop/we%20lit/aquastat/SECURITY.md).

## Contributing

See [CONTRIBUTING.md](/abs/path/C:/Users/matth/OneDrive/Desktop/we%20lit/aquastat/CONTRIBUTING.md).

## License

Server: [LICENSE](/abs/path/C:/Users/matth/OneDrive/Desktop/we%20lit/aquastat/LICENSE)  
SDKs: Apache-2.0 under `sdk/LICENSE`

## Support

Use GitHub Issues for bugs, documentation gaps, and feature requests.
