# Cloud Run Deployment

AquaStat’s Docker image is provider-neutral and can be deployed to Google Cloud Run as a fallback to Render.

## Requirements

- a PostgreSQL database such as Neon
- `AQUASTAT_DATABASE_URL`
- `AQUASTAT_PUBLIC_BASE_URL`
- `AQUASTAT_API_KEY_HASHES`

## Container Expectations

The image already:

- binds to `0.0.0.0`
- respects `PORT`
- serves `/health`, `/health/live`, `/health/ready`, `/openapi.json`, and `/openapi.yaml`
- keeps persistent data in PostgreSQL rather than the container filesystem

## Typical Flow

1. Build and push the Docker image to your registry.
2. Deploy the image to Cloud Run.
3. Set the required environment variables in Cloud Run.
4. Point `AQUASTAT_PUBLIC_BASE_URL` at the verified Cloud Run HTTPS URL.
5. Verify health and OpenAPI endpoints.

## Notes

- Cloud Run filesystem is ephemeral.
- Background polling should remain disabled unless explicitly needed.
- Use an external PostgreSQL database and do not rely on local container storage.
