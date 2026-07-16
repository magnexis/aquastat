# Errors

All production-facing errors use this structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "requestId": "unique-request-id"
  }
}
```

## Standard Error Codes

- `VALIDATION_ERROR`
- `UNAUTHORIZED`
- `FORBIDDEN`
- `NOT_FOUND`
- `METHOD_NOT_ALLOWED`
- `RATE_LIMIT_EXCEEDED`
- `CONFLICT`
- `INTERNAL_SERVER_ERROR`
- `SERVICE_UNAVAILABLE`

Validation responses may also include `details`.
