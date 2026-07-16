# Provider Migration Notes

## Railway to Render/Neon

AquaStat no longer treats Railway as the active deployment target.

Current recommended hosted architecture:

- GitHub for source, releases, and docs
- GitHub Pages for documentation and OpenAPI downloads
- Render for the hosted API
- Neon PostgreSQL for the persistent database

Railway may still appear in historical changelog or migration context, but active deployment guidance should point to Render and Neon.
