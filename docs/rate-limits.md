# Rate Limits

AquaStat applies configurable rate limiting using token-bucket logic.

## Default Tiers

- Anonymous: `60 requests / hour`
- Developer API key: `10,000 requests / day`
- Enterprise signature mode: bypass/custom handling

## Headers

Responses may include:

- `RateLimit-Limit`
- `RateLimit-Remaining`
- `RateLimit-Reset`
- `Retry-After`
- compatibility `X-RateLimit-*` headers

## Error Format

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "The request limit has been exceeded.",
    "requestId": "generated-request-id"
  }
}
```

## Configuration

```env
AQUASTAT_ANONYMOUS_RATE_LIMIT_CAPACITY=60
AQUASTAT_ANONYMOUS_RATE_LIMIT_WINDOW_SECONDS=3600
AQUASTAT_DEVELOPER_RATE_LIMIT_CAPACITY=10000
AQUASTAT_DEVELOPER_RATE_LIMIT_WINDOW_SECONDS=86400
```
