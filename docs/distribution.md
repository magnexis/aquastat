# Distribution

## Positioning

AquaStat is distributed as a backend-first developer product. The main public entry points are the GitHub repository, the backend-served `/docs` interface, the generated `openapi.json`, and the included Postman collection.

## GitHub

Use GitHub as the canonical home for source, issues, changelog, deployment instructions, and self-hosting guidance. The root `README.md` should remain the primary landing page.

## Render and Neon

Render is the recommended hosted API target and Neon is the recommended persistent PostgreSQL provider. After deployment, replace the placeholder base URL in the README, Postman environment example, and marketplace listing drafts with the verified Render public URL.

## Docker and Self-Hosting

Container deployment is supported through the production `Dockerfile`. Teams that need private infrastructure can use Docker directly or adapt the included Terraform starter modules for AWS and GCP.

## Postman Public API Network

Import `postman/AquaStat-API.postman_collection.json`, configure `{{baseUrl}}` and `{{apiKey}}`, verify `/health` and `/api/v1/info`, then publish only after the production URL is finalized.

## RapidAPI

Import `openapi.json`, map marketplace authentication to `X-API-Key`, and validate the documented rate limits and error responses before listing. See `docs/rapidapi-listing.md`.

## SDK Packages

- Python SDK source: `sdk/`
- JavaScript SDK source: `js-sdk/`
- Go SDK source: `go-sdk/`

These packages are prepared in-repo but still require release credentials, registry metadata, and final versioning before publication.

## Marketplace Copy

Short description:
`Water-aware infrastructure API for estimating data center cooling and regional water-impact metrics.`

Support channel:
GitHub Issues

Recommended free tier:
`100 requests per month`

Suggested paid tiers:
`Developer`, `Pro`, and `Business`, as outlined in `docs/rapidapi-listing.md`
