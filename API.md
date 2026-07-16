# API

## Public Operational Routes

- `GET /health`
- `GET /health/live`
- `GET /health/ready`
- `GET /version`
- `GET /docs`
- `GET /openapi.json`

## Control Center Routes

- `GET /control-center`
- `GET /overview`
- `GET /calculate`
- `GET /facilities`
- `GET /api-keys`
- `GET /requests`
- `GET /documentation`
- `GET /api/v1/control-center/overview`
- `GET /api/v1/control-center/models`
- `GET /api/v1/control-center/requests` admin-only
- `GET /api/v1/control-center/api-keys` admin-only
- `POST /api/v1/control-center/api-keys` admin-only
- `POST /api/v1/control-center/api-keys/{keyId}/revoke` admin-only
- `POST /api/v1/control-center/api-keys/{keyId}/disable` admin-only

## Existing AquaStat Routes

The original `/api/v1` and `/api/v2` estimate, facility, footprint, routing, and analytics routes remain preserved.
