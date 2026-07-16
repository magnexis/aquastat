# Railway Deployment

## 1. Fork or Clone

Fork this repository or push it to your own GitHub account.

## 2. Create a Railway Project

Create a new Railway project and connect the GitHub repository.

## 3. Deploy From GitHub

Railway will detect the included `Dockerfile` and `railway.json`.

## 4. Add Environment Variables

At minimum configure:

- `AQUASTAT_ENVIRONMENT=production`
- `AQUASTAT_PUBLIC_BASE_URL=https://YOUR-SERVICE.up.railway.app`
- `AQUASTAT_DATABASE_URL=...`
- `AQUASTAT_REDIS_URL=...`
- `AQUASTAT_REDIS_ENABLED=true`
- `AQUASTAT_API_KEY_HASHES=...`

## 5. Add a Database

Use Railway PostgreSQL if desired, or bring your own Postgres/PostGIS instance.

## 6. Run Migrations

Apply:

```bash
psql "$DATABASE_URL" -f sql/schema.sql
```

## 7. Generate an API Key

```bash
python scripts/generate_api_key.py
```

Store the generated hash in `AQUASTAT_API_KEY_HASHES`.

## 8. Open the Public URL

Railway will generate a public URL such as:

```text
https://YOUR-SERVICE.up.railway.app
```

## 9. Test Health

```bash
curl https://YOUR-SERVICE.up.railway.app/health
```

## 10. Open Docs

Visit:

```text
https://YOUR-SERVICE.up.railway.app/docs
```
