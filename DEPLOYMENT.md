# Deployment

Railway remains the primary hosted target. Docker remains the primary portable packaging target.

## Control Center

The control center is served by the same FastAPI process, so no separate frontend deployment is required. Once the API is up, the control center is available at `/control-center`.

## Required Variables

- `AQUASTAT_ENVIRONMENT`
- `AQUASTAT_PUBLIC_BASE_URL`
- `AQUASTAT_DATABASE_URL`
- `AQUASTAT_REDIS_URL`
- `AQUASTAT_API_KEY_HASHES`
- `AQUASTAT_ADMIN_API_KEY_HASHES` for protected control-center administration

## Durable Ops State

To persist control-center request activity, managed API keys, and audit events:

1. Install the production database dependencies from `pyproject.toml` with `pip install -e .[dev]` or your normal production install flow.
2. Ensure the runtime has PostgreSQL drivers available, especially `asyncpg` for the async app path.
3. Apply the schema in [sql/schema.sql](/abs/path/C:/Users/matth/OneDrive/Desktop/we%20lit/aquastat/sql/schema.sql):

```bash
psql "$DATABASE_URL" -f sql/schema.sql
```

Without the database drivers or migration, AquaStat will fall back to its safe in-memory operational stores for local development.
