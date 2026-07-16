# Source Connectors

Connector metadata is exposed through `/api/v1/sources/connectors`.

Current connector registry tracks:

- source ID
- publisher
- source type
- jurisdiction
- access method
- refresh cadence
- parser version
- terms and restrictions
- last successful fetch
- last failure
- checksum policy
- archival policy

The current implementation is registry-first rather than a broad live crawler.
