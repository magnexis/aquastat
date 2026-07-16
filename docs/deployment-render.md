# Render Deployment

## Overview

The recommended hosted AquaStat deployment path is:

- Render for the API container
- Neon PostgreSQL for the persistent database
- GitHub Pages for public documentation and OpenAPI downloads

## 1. Create the Database

Create a Neon PostgreSQL database and collect:

- pooled connection string for `AQUASTAT_DATABASE_URL`
- direct connection string for `AQUASTAT_DIRECT_DATABASE_URL` if you use a separate migration path

Do not commit either value.

## 2. Create the Render Web Service

Use the repository root and the committed [render.yaml](/C:/Users/matth/OneDrive/Desktop/we%20lit/aquastat/render.yaml) blueprint.

The service should use:

- runtime: Docker
- plan: free or higher
- health check: `/health/ready`

## 3. Configure Environment Variables

At minimum configure:

- `AQUASTAT_ENVIRONMENT=production`
- `AQUASTAT_HOST=0.0.0.0`
- `AQUASTAT_PORT=10000`
- `AQUASTAT_PUBLIC_BASE_URL=https://aquastat-api.onrender.com`
- `AQUASTAT_DATABASE_URL=...`
- `AQUASTAT_REDIS_ENABLED=false`
- `AQUASTAT_API_KEY_HASHES=[\"...\"]`
- `AQUASTAT_ADMIN_API_KEY_HASHES=[\"...\"]`
- `AQUASTAT_CORS_ALLOWED_ORIGINS=[\"https://magnexis.github.io\"]`

## 4. Apply Schema

Apply the committed schema to Neon before expecting durable request logs, managed keys, and audit events:

```bash
psql "$AQUASTAT_DATABASE_URL" -f sql/schema.sql
```

## 5. Verify the Hosted Service

After Render deploys, verify:

```bash
curl https://aquastat-api.onrender.com/health
curl https://aquastat-api.onrender.com/health/ready
curl https://aquastat-api.onrender.com/openapi.json
```

## 6. Update Public References

Once the Render URL is verified, update:

- `README.md`
- `postman/AquaStat-Production.postman_environment.example.json`
- documentation examples
- GitHub repository homepage if desired

## Current Status

The public Render deployment is live at `https://aquastat-api.onrender.com`.
