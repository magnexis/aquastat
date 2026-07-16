# Self Hosting

Use the included `Dockerfile`, `docker-compose.yml`, and `railway.json` as the main starting points.

Self-hosted operators should configure:

- Postgres/PostGIS
- Redis if durable rate-limit and cache state are desired
- regular backups for database state
- admin API key hashes for control-center admin functions
