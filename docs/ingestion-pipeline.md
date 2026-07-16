# Ingestion Pipeline

The Phase 3 ingestion slice currently supports safe dry-run job creation. Jobs validate HTTPS source URLs, reject local or private-network targets, preserve source metadata, and stage work for review instead of mutating published records directly.
