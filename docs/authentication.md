# Authentication

Protected AquaStat endpoints support both:

- `X-API-Key: aq_live_...`
- `Authorization: Bearer aq_live_...`

## Initial Auth Mode

The current production-ready mode uses hashed API keys configured through:

```env
AQUASTAT_API_KEY_HASHES=hash1,hash2
```

Plaintext keys are never stored in the repository.

## Generate a Key

```bash
python scripts/generate_api_key.py
```

This prints:

1. a new plaintext key, shown once
2. the hash to place in `AQUASTAT_API_KEY_HASHES`

## Public Endpoints

These remain publicly accessible:

- `/health`
- `/docs`
- `/redoc`
- `/openapi.json`
- `/api/v1/status`
- `/api/v1/info`
- `/api/v1/regions`

## Protected Endpoints

Core estimate and analytics endpoints require a valid API key when `AQUASTAT_API_KEY_HASHES` is configured.
