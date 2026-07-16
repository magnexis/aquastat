# Changelog

## 1.1.1

- Added production-ready Square billing configuration docs, env examples, and a verifier script for live credential checks
- Extended webhook guidance and tests to cover both `payment.created` and `payment.updated` while only issuing credits after settled payment states
- Tightened quota exhaustion behavior so `429` remains deny-only while project-backed `402` responses can surface a refill checkout link
- Removed the unused pytest `asyncio_mode` config warning and synchronized package/runtime metadata to `1.1.1`

## 1.1.0

- Added a first-party `aquastat` CLI with status, region, estimate, facility, and workload-routing commands
- Refreshed the desktop analyst shell with stronger presentation, browsing flow, and multi-panel intelligence views
- Updated docs and install guidance so desktop and CLI usage are first-class product surfaces
- Bumped package and runtime metadata to `1.1.0`

## 1.0.1

- Rebuilt the desktop shell into a multi-panel facility intelligence workspace with browsing, evidence, sources, history, and public-record views
- Added branded desktop assets, logo artwork, and improved desktop entry-point structure
- Fixed stale static docs-site deployment references and added repeatable release asset packaging
- Aligned API, SDK, desktop, and WASM version metadata for the updated release

## 1.0.0

- Standardized production metadata routes and health checks
- Added request IDs, centralized errors, and typed configuration
- Added API-key authentication flow and key generation script
- Added Railway deployment metadata, Postman assets, and examples
- Added documentation set for deployment, auth, errors, rate limits, and distribution
