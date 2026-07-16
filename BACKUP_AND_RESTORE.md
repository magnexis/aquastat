# Backup and Restore

Back up:

- PostgreSQL database
- Redis if durable operational state matters
- deployment environment variables stored in the hosting provider

The in-memory control-center operational stores added in this phase are not durable and are repopulated only during runtime.
