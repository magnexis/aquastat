# Runbook

## Health Checks

- `/health`
- `/health/live`
- `/health/ready`
- `/version`

## Operational Notes

- request history is currently in rolling in-memory retention
- managed control-center API keys are currently in-memory and intended for operator workflows, not long-term persistence
- admin functions require `AQUASTAT_ADMIN_API_KEY_HASHES`
