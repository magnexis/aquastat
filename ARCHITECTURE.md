# Architecture

## Current Stack

- Backend: FastAPI on Python 3.11+
- Data layer: PostgreSQL/PostGIS with seed-backed fallbacks
- Cache and rate limiting: Redis with in-memory fallback
- Observability: structured logs, Prometheus metrics, request IDs
- Distribution: Docker, Railway, SDK source packages, Terraform starter modules
- Control Center: backend-served HTML workspace that talks only to AquaStat API endpoints

## Control Center

The AquaStat Control Center is intentionally thin. It does not contain duplicated calculation logic. It renders a backend-served interface and uses live AquaStat API routes for overview metrics, estimates, facilities, model registry, request history, and managed API key actions.

## API and Model Flow

1. Requests enter FastAPI through structured middleware.
2. Request IDs, rate limits, security headers, and auth checks are applied.
3. Business routes call the thermodynamic or facility-intelligence service layer.
4. The model version and dataset versions are returned with estimates.
5. Request activity is recorded in rolling in-memory operational storage for the control center.
